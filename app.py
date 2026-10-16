"""Interface local do Ritmo. Execute python app.py e abra o endereço exibido."""
import argparse
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import sys
from urllib.parse import urlsplit
from data_sources import open_source, csv_source, SourceError
from finance_bot import FinanceBot

ROOT=Path(__file__).resolve().parent
ASSETS={'/':('index.html','text/html'),'/index.html':('index.html','text/html'),
        '/app.js':('app.js','text/javascript'),'/styles.css':('styles.css','text/css')}


class Application:
    def __init__(self,source):
        self.bot=FinanceBot(source)

    def ask(self,payload):
        return self.bot.ask(payload.get('question'))

    def load_csv(self,payload):
        content=payload.get('content')
        if not isinstance(content,str) or len(content.encode('utf-8'))>1_000_000:
            raise SourceError('Selecione um CSV UTF-8 de até 1 MB.')
        name=payload.get('name','despesas.csv')
        if not isinstance(name,str):raise SourceError('Nome do arquivo inválido.')
        new_source=csv_source(content,name)
        overview=new_source.snapshot()
        self.bot.source.close()
        self.bot.source=new_source
        return overview


def handler_for(application):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass  # Do not record financial questions in request logs.

        def allowed_host(self):
            port=self.server.server_port
            return self.headers.get('Host') in (f'127.0.0.1:{port}',f'localhost:{port}')

        def respond(self,status,body,content_type='application/json'):
            if content_type=='application/json':body=json.dumps(body,ensure_ascii=False).encode('utf-8')
            self.send_response(status)
            self.send_header('Content-Type',content_type+'; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'")
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self.allowed_host():return self.respond(403,{'error':'Host não autorizado.'})
            route=urlsplit(self.path).path
            if route=='/api/overview':
                try:return self.respond(200,application.bot.overview())
                except SourceError as error:return self.respond(400,{'error':str(error)})
            if route in ASSETS:
                name,kind=ASSETS[route]
                return self.respond(200,(ROOT/'web'/name).read_bytes(),kind)
            return self.respond(404,{'error':'Página não encontrada.'})

        def do_POST(self):
            if not self.allowed_host():return self.respond(403,{'error':'Host não autorizado.'})
            origin=self.headers.get('Origin')
            if origin and origin not in (f'http://127.0.0.1:{self.server.server_port}',f'http://localhost:{self.server.server_port}'):
                return self.respond(403,{'error':'Origem não autorizada.'})
            if self.headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.respond(415,{'error':'Envie JSON.'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=1_100_000:raise ValueError('Tamanho inválido.')
                payload=json.loads(self.rfile.read(size).decode('utf-8'))
                if not isinstance(payload,dict):raise ValueError('Envie um objeto JSON.')
                route=urlsplit(self.path).path
                if route=='/api/chat':return self.respond(200,application.ask(payload))
                if route=='/api/data':return self.respond(200,application.load_csv(payload))
                return self.respond(404,{'error':'Operação não encontrada.'})
            except (ValueError,UnicodeDecodeError,SourceError) as error:
                return self.respond(400,{'error':str(error)})
    return Handler


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',choices=('csv','sqlite','postgres'),default='csv')
    parser.add_argument('--input',type=Path)
    parser.add_argument('--port',type=int,default=4321)
    args=parser.parse_args()
    try:
        application=Application(open_source(args.source,args.input))
        server=HTTPServer(('127.0.0.1',args.port),handler_for(application))
    except (OSError,SourceError) as error:
        print('Não foi possível iniciar: '+str(error),file=sys.stderr)
        return 2
    print(f'Ritmo local: http://127.0.0.1:{args.port}/\nCtrl+C para encerrar. Os dados ficam neste processo.')
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        server.server_close()
        application.bot.source.close()
    return 0


if __name__=='__main__':sys.exit(main())
