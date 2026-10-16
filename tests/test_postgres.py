"""Integração em PostgreSQL descartável do CI, sem conexão a empresas."""
import os
import unittest
from data_sources import postgres_source


@unittest.skipUnless(os.environ.get('RITMO_TEST_POSTGRES')=='1','PostgreSQL de teste não configurado')
class PostgresIntegrationTests(unittest.TestCase):
    def test_aggregations_and_read_only_connection(self):
        import psycopg
        with psycopg.connect(os.environ['RITMO_DATABASE_URL'],autocommit=True) as setup:
            setup.execute('''CREATE TABLE IF NOT EXISTS finance_expenses(expense_id TEXT PRIMARY KEY,
                expense_date TEXT,category TEXT,supplier TEXT,amount_cents BIGINT,status TEXT)''')
            setup.execute('TRUNCATE finance_expenses')
            with setup.cursor() as cursor:
                cursor.executemany('INSERT INTO finance_expenses VALUES(%s,%s,%s,%s,%s,%s)',
                    [('A','2026-01-01','Tecnologia','Demo',12345,'pago'),
                     ('B','2026-02-01','Marketing','Demo',5000,'pendente')])
        source=postgres_source()
        try:
            self.assertEqual(source.snapshot()['summary']['paid_cents'],12345)
            self.assertEqual(source.snapshot(['2026-02'])['summary']['pending_cents'],5000)
            self.assertEqual(source.snapshot(categories=['Tecnologia'])['summary']['records'],1)
            with self.assertRaises(psycopg.errors.ReadOnlySqlTransaction):
                source.connection.execute('DELETE FROM finance_expenses')
        finally:source.close()


if __name__=='__main__':unittest.main()
