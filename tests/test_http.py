"""API local em um servidor temporário, incluindo limites de origem e arquivos."""
from http.server import HTTPServer
import json
import queue
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import Request,urlopen
from app import Application,handler_for
from data_sources import open_source


class HTTPTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        ready=queue.Queue()
        def run():
            application=Application(open_source())
            try:
                server=HTTPServer(('127.0.0.1',0),handler_for(application))
                ready.put(server)
                server.serve_forever(poll_interval=0.05)
                server.server_close()
            except OSError as error:ready.put(error)
            finally:application.bot.source.close()
        cls.thread=threading.Thread(target=run,daemon=True)
        cls.thread.start()
        result=ready.get(timeout=10)
        if isinstance(result,Exception):raise result
        cls.server=result
        cls.base='http://127.0.0.1:'+str(result.server_port)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown();cls.thread.join(timeout=5)

    def test_question_returns_numbers_and_evidence(self):
        request=Request(self.base+'/api/chat',data=json.dumps({'question':'Quanto gastamos em fevereiro de 2026?'}).encode(),headers={'Content-Type':'application/json'})
        with urlopen(request,timeout=5) as response:
            data=json.load(response)
            self.assertIn('R$ 4.625,70',data['text'])
            self.assertEqual(data['evidence']['source'],'expenses.csv')

    def test_external_origins_cannot_upload(self):
        request=Request(self.base+'/api/data',data=b'{}',headers={'Content-Type':'application/json','Origin':'https://example.org'})
        with self.assertRaises(HTTPError) as error:urlopen(request,timeout=5)
        self.assertEqual(error.exception.code,403)
        error.exception.close()

    def test_static_routes_do_not_expose_project_files(self):
        with self.assertRaises(HTTPError) as error:urlopen(self.base+'/data/train.json',timeout=5)
        self.assertEqual(error.exception.code,404)
        error.exception.close()


if __name__=='__main__':unittest.main()
