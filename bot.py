"""Demonstração do chatbot financeiro no terminal, sem servidor ou API externa."""
import argparse
import json
from pathlib import Path
from data_sources import open_source
from finance_bot import FinanceBot

EXAMPLES=('Quanto gastamos em fevereiro de 2026?', 'Mostre os gastos por categoria',
          'Compare os gastos por mês', 'Quais foram as maiores despesas?', 'Há erros na planilha?')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('demo','chat'),default='demo',nargs='?')
    parser.add_argument('--source',choices=('csv','sqlite','postgres'),default='csv')
    parser.add_argument('--input',type=Path)
    args=parser.parse_args()
    source=open_source(args.source,args.input)
    bot=FinanceBot(source)
    try:
        if args.mode=='demo':
            print('RITMO · DEMONSTRAÇÃO LOCAL · DADOS FICTÍCIOS' if source.demo else 'RITMO · FONTE SELECIONADA')
            for question in EXAMPLES:
                print('\nVocê: '+question)
                print('Ritmo: '+bot.ask(question)['text'])
        else:
            print('Escreva sua pergunta. Use /sair para encerrar.')
            while True:
                question=input('Você: ')
                if question.strip()=='/sair':break
                print('Ritmo: '+bot.ask(question)['text'])
    except (KeyboardInterrupt,EOFError):
        pass
    finally:
        source.close()


if __name__=='__main__':main()
