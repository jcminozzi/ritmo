"""Bot simples para consultar indicadores de vendas de um relatório do Pulso."""
import argparse
from io import StringIO
import json
import os
from pathlib import Path
import sqlite3
import sys
from urllib.error import HTTPError,URLError
from urllib.request import Request,urlopen

def money(cents):return f'R$ {cents/100:.2f}'.replace('.',',')


class SalesBot:
    def __init__(self,report,database=':memory:',notes=None):
        self.report=report if isinstance(report,dict) else json.loads(Path(report).read_text(encoding='utf-8'))
        summary=self.report.get('summary',{})
        for key in ('completed_orders','revenue_cents','average_order_cents','cancelled_orders'):
            if type(summary.get(key)) is not int or summary[key]<0:raise ValueError('indicadores inválidos no relatório')
        if not isinstance(self.report.get('by_category'),list):raise ValueError('categorias inválidas')
        self.notes=json.loads(Path(notes).read_text(encoding='utf-8')) if notes else None
        self.db=sqlite3.connect(database)
        self.db.execute('CREATE TABLE IF NOT EXISTS metadata(key TEXT PRIMARY KEY,value TEXT)')
    def close(self):self.db.close()
    def handle(self,chat,text):
        command=text.strip().split(maxsplit=1)[0].split('@',1)[0].lower() if text.strip() else '/ajuda'
        summary=self.report['summary']
        if command in ('/start','/ajuda'):
            return 'Ritmo: consulte o relatório de vendas.\n/vendas - indicadores\n/categorias - receita por categoria\n/resumo - leitura dos resultados\n/qualidade - conferência dos dados'
        if command=='/vendas':
            return (f"Receita concluída: {money(summary['revenue_cents'])}\n"
                    f"Pedidos concluídos: {summary['completed_orders']}\n"
                    f"Ticket médio: {money(summary['average_order_cents'])}\n"
                    f"Pedidos cancelados: {summary['cancelled_orders']}")
        if command=='/categorias':
            rows=self.report['by_category'][:5]
            return 'Receita por categoria:\n'+'\n'.join(f"{r['category']}: {money(r['revenue_cents'])}" for r in rows) if rows else 'Sem categorias com vendas concluídas.'
        if command=='/resumo':
            if self.notes:
                comments=[str(item['comment']) for item in self.notes.get('observations',[]) if isinstance(item,dict) and isinstance(item.get('comment'),str)]
                return ('Rascunho de IA do Pulso, para revisão:\n'+'\n'.join(comments))[:3500]
            top=self.report['by_category'][0]['category'] if self.report['by_category'] else 'Nenhuma categoria'
            return (f"{top} teve a maior receita no conjunto. "
                    f"{summary['cancelled_orders']} pedidos cancelados ficaram fora da receita. "
                    'Resumo calculado por regras. Esta demonstração usa dados fictícios.')
        if command=='/qualidade':
            return (f"Linhas recebidas: {self.report.get('input_rows',0)}\n"
                    f"Linhas válidas: {self.report.get('valid_rows',0)}\n"
                    f"Linhas para revisão: {len(self.report.get('issues',[]))}")
        return 'Use /ajuda para ver os comandos disponíveis.'
    def offset(self):
        value=self.db.execute("SELECT value FROM metadata WHERE key='offset'").fetchone()
        return int(value[0]) if value else 0
    def save_offset(self,value):
        with self.db:self.db.execute('INSERT OR REPLACE INTO metadata VALUES(?,?)',('offset',str(value)))


def reply_for(bot,update,allowed_chat):
    message=update.get('message')
    if not isinstance(message,dict):return None
    chat=message.get('chat',{})
    if chat.get('type')!='private' or str(chat.get('id'))!=str(allowed_chat):return None
    text=message.get('text')
    if not isinstance(text,str) or not text.strip():return None
    return bot.handle(chat['id'],text)


class TelegramError(RuntimeError):pass


class TelegramClient:
    def __init__(self,token,opener=None):
        if not token.strip():raise TelegramError('Configure TELEGRAM_BOT_TOKEN no ambiente.')
        self.token=token;self.opener=opener or urlopen
    def call(self,method,body):
        if method not in ('getUpdates','sendMessage'):raise TelegramError('Método não permitido neste protótipo.')
        request=Request('https://api.telegram.org/bot'+self.token+'/'+method,
                        data=json.dumps(body).encode(),headers={'Content-Type':'application/json'},method='POST')
        try:
            with self.opener(request,timeout=35) as response:data=json.loads(response.read().decode('utf-8'))
        except HTTPError as exc:raise TelegramError(f'Telegram retornou HTTP {exc.code}.') from None
        except (URLError,OSError,ValueError):raise TelegramError('Falha de conexão ou resposta inválida do Telegram.') from None
        if not isinstance(data,dict) or data.get('ok') is not True:raise TelegramError('Telegram não confirmou a operação.')
        return data.get('result')


def telegram_loop(bot,client,chat_id):
    offset=bot.offset()
    while True:
        updates=client.call('getUpdates',{'timeout':20,'offset':offset,'allowed_updates':['message']})
        if not isinstance(updates,list):raise TelegramError('Lista de atualizações inválida.')
        for update in updates:
            if not isinstance(update,dict) or type(update.get('update_id')) is not int:continue
            if update['update_id']<offset:continue
            reply=reply_for(bot,update,chat_id)
            if reply:client.call('sendMessage',{'chat_id':chat_id,'text':reply})
            offset=update['update_id']+1;bot.save_offset(offset)


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('demo','telegram'))
    parser.add_argument('--db',type=Path,default=Path('outputs/ritmo.db'))
    parser.add_argument('--chat-id',type=int)
    parser.add_argument('--report',type=Path,default=Path('samples/report.json'))
    parser.add_argument('--notes',type=Path)
    args=parser.parse_args(argv)
    if args.mode=='telegram' and args.chat_id is None:parser.error('telegram exige --chat-id da sua conversa privada')
    args.db.parent.mkdir(parents=True,exist_ok=True)
    try:bot=SalesBot(args.report,str(args.db),args.notes)
    except (OSError,ValueError) as exc:print('Erro: '+str(exc),file=sys.stderr);return 2
    try:
        if args.mode=='demo':
            # Fixed local conversation. No Telegram call or token is needed.
            for command in ('/start','/vendas','/categorias','/resumo','/qualidade'):
                print('Você: '+command);print('Ritmo: '+bot.handle('demo',command)+'\n')
        else:
            client=TelegramClient(os.environ.get('TELEGRAM_BOT_TOKEN',''))
            print('Ritmo ativo para a conversa privada configurada. Ctrl+C para encerrar.')
            telegram_loop(bot,client,args.chat_id)
        return 0
    except KeyboardInterrupt:print('Ritmo encerrado. Execução encerrada.');return 0
    except (TelegramError,sqlite3.Error,OSError) as exc:print('Erro: '+str(exc),file=sys.stderr);return 2
    finally:bot.close()


if __name__=='__main__':sys.exit(main())
