"""Fontes de dados com o mesmo contrato: CSV, SQLite e PostgreSQL opcional."""
import csv
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
import io
import os
from pathlib import Path
import re
import sqlite3

COLUMNS = ('expense_id','expense_date','category','supplier','amount_cents','status')
CSV_COLUMNS = ('expense_id','date','category','supplier','amount','status')
ROOT = Path(__file__).resolve().parent


class SourceError(ValueError):
    pass


class SQLSource:
    def __init__(self, connection, dialect, name, issues=None, demo=False):
        self.connection = connection
        self.dialect = dialect
        self.name = name
        self.issues = issues
        self.demo = demo
        try:
            self._fetch('SELECT '+','.join(COLUMNS)+' FROM finance_expenses LIMIT 0')
        except Exception:
            connection.close()
            raise SourceError('A fonte precisa da tabela ou view finance_expenses com as colunas documentadas.') from None

    def _fetch(self, sql, parameters=()):
        cursor = self.connection.cursor()
        try:
            cursor.execute(sql, parameters)
            names = [column[0] for column in cursor.description]
            return [dict(zip(names, row)) for row in cursor.fetchall()]
        finally:
            cursor.close()

    def snapshot(self, months=(), categories=()):
        # Queries are fixed in code. Question text is never SQL.
        placeholder = '?' if self.dialect == 'sqlite' else '%s'
        if any(not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])', month) for month in months):
            raise SourceError('Filtro de mês inválido.')
        clauses, parameters = [], []
        if months:
            clauses.append('substr(expense_date,1,7) IN ('+','.join([placeholder]*len(months))+')')
            parameters.extend(months)
        if categories:
            clauses.append('category IN ('+','.join([placeholder]*len(categories))+')')
            parameters.extend(categories)
        where = ' WHERE '+' AND '.join(clauses) if clauses else ''
        paid = where + (' AND ' if where else ' WHERE ') + "status='pago'"
        try:
            summary = self._fetch('''SELECT COUNT(*) AS records,
                COALESCE(SUM(CASE WHEN status='pago' THEN amount_cents ELSE 0 END),0) AS paid_cents,
                COALESCE(SUM(CASE WHEN status='pendente' THEN amount_cents ELSE 0 END),0) AS pending_cents,
                SUM(CASE WHEN status='pago' THEN 1 ELSE 0 END) AS paid_count
                FROM finance_expenses'''+where, tuple(parameters))[0]
            categories = self._fetch('SELECT category AS label,SUM(amount_cents) AS cents FROM finance_expenses'+paid+
                                     ' GROUP BY category ORDER BY cents DESC,category LIMIT 8', tuple(parameters))
            monthly = self._fetch('SELECT substr(expense_date,1,7) AS label,SUM(amount_cents) AS cents FROM finance_expenses'+paid+
                                  ' GROUP BY substr(expense_date,1,7) ORDER BY label DESC LIMIT 12', tuple(parameters))
            largest = self._fetch('SELECT expense_id,supplier,category,expense_date,amount_cents FROM finance_expenses'+paid+
                                  ' ORDER BY amount_cents DESC,expense_id LIMIT 5', tuple(parameters))
            ids = self._fetch('SELECT expense_id FROM finance_expenses'+paid+' ORDER BY expense_id LIMIT 12', tuple(parameters))
            years = self._fetch('SELECT DISTINCT substr(expense_date,1,4) AS year FROM finance_expenses ORDER BY year')
            catalog = self._fetch('SELECT DISTINCT category FROM finance_expenses ORDER BY category LIMIT 200')
        except Exception:
            raise SourceError('Não foi possível consultar a fonte de dados. Confira o contrato das colunas e a conexão.') from None
        return {'summary':summary, 'categories':categories, 'months':list(reversed(monthly)),
                'largest':largest, 'sample_ids':[row['expense_id'] for row in ids],
                'years':[row['year'] for row in years], 'available_categories':[row['category'] for row in catalog],
                'source':self.name, 'demo':self.demo,
                'issues':self.issues, 'filters':list(months),
                'queried_at':datetime.now(timezone.utc).isoformat(timespec='seconds')}

    def close(self):
        self.connection.close()


def csv_source(content, name='despesas.csv', demo=False):
    reader = csv.DictReader(io.StringIO(content.lstrip('\ufeff')))
    if tuple(reader.fieldnames or ()) != CSV_COLUMNS:
        raise SourceError('O CSV precisa das colunas, na ordem: '+', '.join(CSV_COLUMNS))
    rows, issues, seen = [], [], set()
    for line, row in enumerate(reader, 2):
        if line > 5001:
            raise SourceError('Esta demonstração aceita até 5.000 linhas por CSV.')
        try:
            identifier = row['expense_id'].strip()
            if not identifier or identifier in seen:
                raise ValueError('identificador vazio ou duplicado')
            day = date.fromisoformat(row['date'].strip()).isoformat()
            category, supplier = row['category'].strip(), row['supplier'].strip()
            if not category or not supplier or max(len(category),len(supplier))>160:
                raise ValueError('categoria ou fornecedor ausente ou longo demais')
            amount = row['amount'].strip()
            if not re.fullmatch(r'\d+\.\d{2}', amount):
                raise ValueError('valor precisa de ponto e duas casas decimais')
            cents = int(Decimal(amount)*100)
            if not 0<cents<=100000000000:
                raise ValueError('valor fora do intervalo do protótipo')
            status = row['status'].strip().lower()
            if status not in ('pago','pendente'):
                raise ValueError('status precisa ser pago ou pendente')
            rows.append((identifier,day,category,supplier,cents,status))
            seen.add(identifier)
        except (KeyError,ValueError,AttributeError,InvalidOperation) as error:
            issues.append({'line':line,'reason':str(error)})
    db = sqlite3.connect(':memory:')
    db.execute('''CREATE TABLE finance_expenses(expense_id TEXT PRIMARY KEY,expense_date TEXT,
                  category TEXT,supplier TEXT,amount_cents INTEGER,status TEXT)''')
    db.executemany('INSERT INTO finance_expenses VALUES(?,?,?,?,?,?)', rows)
    db.commit()
    db.execute('PRAGMA query_only=ON')
    return SQLSource(db,'sqlite',Path(name).name[:100],issues,demo)


def sqlite_source(path):
    try:
        connection = sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True)
        connection.execute('PRAGMA query_only=ON')
    except sqlite3.Error:
        raise SourceError('Não foi possível abrir o SQLite em modo de leitura.') from None
    return SQLSource(connection,'sqlite','SQLite · finance_expenses')


def postgres_source(connector=None):
    dsn = os.environ.get('RITMO_DATABASE_URL','')
    if not dsn:
        raise SourceError('Configure RITMO_DATABASE_URL no ambiente local.')
    if connector is None:
        try:
            import psycopg
            connector = psycopg.connect
        except ImportError:
            raise SourceError('Instale requirements-postgres.txt para usar PostgreSQL.') from None
    try:
        connection = connector(dsn,connect_timeout=5,autocommit=True,
                               options='-c default_transaction_read_only=on -c statement_timeout=3000')
    except Exception:
        raise SourceError('Falha ao conectar ao PostgreSQL. Confira a configuração local.') from None
    return SQLSource(connection,'postgres','PostgreSQL · finance_expenses')


def open_source(kind='csv',path=None):
    if kind=='postgres':
        return postgres_source()
    if kind=='sqlite':
        if path is None:raise SourceError('Informe --input com o caminho do SQLite.')
        return sqlite_source(path)
    target = Path(path) if path else ROOT/'samples/expenses.csv'
    return csv_source(target.read_text(encoding='utf-8-sig'),target.name,demo=path is None)
