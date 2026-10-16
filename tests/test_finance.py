import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch
from app import Application
from data_sources import csv_source,open_source,postgres_source,sqlite_source,SourceError
from finance_bot import FinanceBot,month_filters
from intent_model import IntentModel

HEADER='expense_id,date,category,supplier,amount,status\n'
ROWS='A,2026-01-02,Tecnologia,Demo,0.10,pago\nB,2026-02-02,Marketing,Demo,0.20,pago\nC,2026-02-03,Marketing,Demo,10.00,pendente\n'


class FinanceTests(unittest.TestCase):
    def setUp(self):
        self.source=csv_source(HEADER+ROWS)
        self.addCleanup(self.source.close)

    def test_paid_and_pending_are_separated_in_exact_cents(self):
        summary=self.source.snapshot()['summary']
        self.assertEqual(summary['paid_cents'],30)
        self.assertEqual(summary['pending_cents'],1000)

    def test_duplicates_bad_dates_and_missing_values_are_quarantined(self):
        source=csv_source(HEADER+ROWS+'A,2026-01-01,T,D,1.00,pago\nD,2026-02-30,T,D,1.00,pago\nE,2026-01-01,T,D,,pago\n')
        self.addCleanup(source.close)
        self.assertEqual(len(source.issues),3)
        self.assertEqual(source.snapshot()['summary']['records'],3)

    def test_month_filter_excludes_other_months(self):
        self.assertEqual(self.source.snapshot(['2026-02'])['summary']['paid_cents'],20)

    def test_category_filter_is_parameterized(self):
        self.assertEqual(self.source.snapshot(categories=['Marketing'])['summary']['paid_cents'],20)
        self.assertEqual(self.source.snapshot(categories=["x' OR 1=1 --"])['summary']['records'],0)
        self.assertEqual(self.source.snapshot()['summary']['records'],3)

    def test_no_paid_records_is_defined(self):
        self.assertEqual(self.source.snapshot(['2027-01'])['summary']['paid_cents'],0)

    def test_invalid_month_cannot_be_sql(self):
        with self.assertRaises(SourceError):self.source.snapshot(["2026-01' OR 1=1"])

    def test_local_source_cannot_write_after_loading(self):
        with self.assertRaises(sqlite3.OperationalError):self.source.connection.execute('DELETE FROM finance_expenses')

    def test_sqlite_file_is_opened_read_only(self):
        temporary_root=Path(__file__).resolve().parents[1]/'outputs'
        temporary_root.mkdir(exist_ok=True)
        with TemporaryDirectory(dir=temporary_root) as folder:
            path=Path(folder)/'finance.db'
            target=sqlite3.connect(path)
            self.source.connection.backup(target);target.close()
            source=sqlite_source(path)
            try:
                self.assertEqual(source.snapshot()['summary']['paid_cents'],30)
                with self.assertRaises(sqlite3.OperationalError):source.connection.execute('DELETE FROM finance_expenses')
            finally:source.close()

    def test_postgres_requests_read_only_and_timeout(self):
        captured={}
        def connect(dsn,**kwargs):
            captured.update(kwargs)
            raise RuntimeError('credential-value-must-not-leak')
        with patch.dict(os.environ,{'RITMO_DATABASE_URL':'private-example-only'}):
            with self.assertRaises(SourceError) as error:postgres_source(connect)
        self.assertIn('default_transaction_read_only=on',captured['options'])
        self.assertIn('statement_timeout=3000',captured['options'])
        self.assertNotIn('credential-value',str(error.exception))

    def test_failed_upload_preserves_previous_source(self):
        app=Application(self.source)
        with self.assertRaises(SourceError):app.load_csv({'content':'bad header','name':'bad.csv'})
        self.assertEqual(app.bot.overview()['summary']['paid_cents'],30)

    def test_month_names_need_a_year_if_source_has_multiple_years(self):
        with self.assertRaises(ValueError):month_filters('Gastos em janeiro',['2025','2026'])
        self.assertEqual(month_filters('Janeiro de 2026',['2025','2026']),['2026-01'])

    def test_relative_dates_and_invalid_months_require_clarification(self):
        for text in ('gastos de hoje','gastos em 2026-13'):
            with self.subTest(text=text):
                with self.assertRaises(ValueError):month_filters(text,['2026'])

    def test_unknown_vocabulary_abstains(self):
        self.assertEqual(IntentModel.load(Path(__file__).resolve().parents[1]/'model/intent-model.json').predict('xyzabc qwerty')['intent'],'unclear')

    def test_training_changes_learned_weights(self):
        model=IntentModel.train([{'question':'gastos despesas','intent':'finance'},{'question':'chuva sol','intent':'weather'}])
        self.assertEqual(model.predict('gastos despesas')['intent'],'finance')
        self.assertEqual(model.predict('chuva sol')['intent'],'weather')

    def test_answer_cites_source_and_uses_computed_values(self):
        bot=FinanceBot(self.source)
        result=bot.ask('Qual é o total gasto')
        self.assertEqual(result['kind'],'answer')
        self.assertIn('R$ 0,30',result['text'])
        self.assertEqual(result['evidence']['source'],'despesas.csv')
        self.assertEqual(result['evidence']['sample_ids'],['A','B'])

    def test_category_in_question_filters_the_calculation(self):
        result=FinanceBot(self.source).ask('Qual é o total gasto em Marketing')
        self.assertIn('R$ 0,20',result['text'])
        self.assertIn('Marketing',result['scope'])

    def test_unsupported_exclusions_do_not_silently_change_scope(self):
        result=FinanceBot(self.source).ask('Qual é o total gasto exceto Marketing')
        self.assertEqual(result['kind'],'clarify')


if __name__=='__main__':unittest.main()
