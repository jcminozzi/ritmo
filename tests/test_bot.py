from io import BytesIO
import json
import unittest
from urllib.error import HTTPError
from bot import SalesBot,TelegramClient,TelegramError,reply_for

class BotTests(unittest.TestCase):
    def setUp(self):self.bot=SalesBot('samples/report.json');self.addCleanup(self.bot.close)
    def test_sales_show_computed_revenue(self):self.assertIn('2426,10',self.bot.handle(1,'/vendas'))
    def test_categories_are_visible(self):self.assertIn('Livros',self.bot.handle(1,'/categorias'))
    def test_quality_separates_invalid_rows(self):self.assertIn('Linhas para revisão: 3',self.bot.handle(1,'/qualidade'))
    def test_local_summary_is_not_claimed_as_ai(self):self.assertIn('por regras',self.bot.handle(1,'/resumo'))
    def test_help_explains_commands(self):self.assertIn('/vendas',self.bot.handle(1,'/start'))
    def test_unknown_command_is_handled(self):self.assertIn('/ajuda',self.bot.handle(1,'/desconhecido'))
    def test_groups_and_other_chats_are_ignored(self):
        for chat in ({'id':1,'type':'group'},{'id':2,'type':'private'}):
            self.assertIsNone(reply_for(self.bot,{'message':{'chat':chat,'text':'/quiz'}},1))
    def test_offset_is_saved(self):self.bot.save_offset(42);self.assertEqual(self.bot.offset(),42)
    def test_client_encodes_plain_text(self):
        def opener(request,timeout):
            data=json.loads(request.data);self.assertEqual(data['text'],'Olá');self.assertEqual(timeout,35)
            return BytesIO(b'{"ok":true,"result":{"message_id":1}}')
        self.assertEqual(TelegramClient('test-only',opener).call('sendMessage',{'chat_id':1,'text':'Olá'})['message_id'],1)
    def test_http_error_does_not_leak_token(self):
        def fail(*args,**kwargs):raise HTTPError('secret-url',401,'token-value',{},None)
        with self.assertRaises(TelegramError) as error:TelegramClient('private-test-token',fail).call('getUpdates',{})
        self.assertNotIn('private-test-token',str(error.exception));self.assertNotIn('secret-url',str(error.exception))

if __name__=='__main__':unittest.main()
