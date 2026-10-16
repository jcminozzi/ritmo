# Trocar a fonte de dados

O chatbot trabalha com uma estrutura única de despesas. Cada conexão oferece essa estrutura. As perguntas não viram SQL livre: a aplicação escolhe consultas fixas e usa parâmetros para os filtros.

## 1. CSV — experimentar sem configurar banco

```powershell
python app.py
```

Abra o endereço exibido e use **Carregar outro CSV**. O arquivo é lido em memória, sem alterar o original. A base inicial é fictícia. O modelo de CSV está em `samples/expenses.csv`.

| Coluna | Exemplo |
|---|---|
| expense_id | D001 |
| date | 2026-02-10 |
| category | Tecnologia |
| supplier | Fornecedor Demo A |
| amount | 289.00 |
| status | pago |

Use as colunas nessa ordem, datas ISO, valores positivos com ponto e duas casas decimais e status `pago` ou `pendente`. Limite do importador: 1 MB pela tela e até 5.000 linhas. Duplicatas, campos ausentes e valores ou datas inválidos são separados para revisão.

## 2. SQLite — um banco local

Para praticar com dados fictícios:

```powershell
python connect.py outputs/demo.db
python app.py --source sqlite --input outputs/demo.db
```

O primeiro comando cria um arquivo novo e não sobrescreve arquivos existentes. O segundo abre o banco em modo de leitura. Um banco existente precisa oferecer a tabela ou view `finance_expenses` com o contrato abaixo.

## 3. PostgreSQL — adaptador para uma fonte SQL

```powershell
python -m pip install -r requirements-postgres.txt
python app.py --source postgres
```

Antes de executar, configure **RITMO_DATABASE_URL** no ambiente do computador, com a conexão fornecida por quem administra o banco. Use uma conta com permissão de leitura apenas sobre a view financeira e a configuração TLS definida para esse ambiente. Não coloque credenciais no código, no GitHub, em prints ou na conversa.

O adaptador pede transações de leitura, limita cada consulta a três segundos e usa timeout de conexão de cinco segundos. As credenciais não são mostradas na tela. A conexão não precisa copiar toda a tabela para o chatbot: somas e agrupamentos são executados no banco.

## Contrato da view finance_expenses

| Coluna | Tipo esperado | Regra |
|---|---|---|
| expense_id | texto | Identificador único |
| expense_date | texto | Data válida em AAAA-MM-DD |
| category | texto | Nome da categoria |
| supplier | texto | Nome do fornecedor |
| amount_cents | inteiro | Valor positivo em centavos |
| status | texto | pago ou pendente |

A equipe responsável pela base adapta uma view às colunas da empresa. Há um exemplo comentado em [postgres-view.sql](postgres-view.sql). O chatbot confere a presença das colunas; a qualidade dos valores da view continua sendo responsabilidade dessa preparação. A limpeza linha a linha ocorre no importador CSV.

Nesta versão, SQLite e PostgreSQL estão implementados. MySQL, SQL Server e ERPs exigem novos adaptadores e testes. Não existe detecção automática de qualquer esquema de empresa.

## Como a informação se mantém atualizada

Cada pergunta consulta a fonte selecionada naquele momento. A resposta informa o horário e os filtros. O CSV permanece como uma fotografia da importação; carregue-o de novo para atualizar. Os cartões do topo mostram o conjunto completo; o gráfico da resposta pode ter um recorte por mês ou categoria.

As consultas limitam os gráficos a oito categorias, os meses a 12 e os maiores lançamentos a cinco. Para bases grandes, índices e uma view adequada precisam ser avaliados com quem administra o banco. Nenhum ganho de velocidade em ambiente empresarial foi medido.

## Verificação

Os testes locais cobrem CSV, SQLite, filtros e bloqueio de escrita. O workflow inclui PostgreSQL descartável com dados fictícios, consulta real e tentativa de escrita rejeitada. Verifique o resultado da execução em [Actions](https://github.com/jcminozzi/ritmo/actions). Não houve conexão a banco de empresa.

O servidor usa somente `127.0.0.1`, sem autenticação ou implantação pública. Esta é uma demonstração de estudo para usar no próprio computador.

Referências: [sqlite3](https://docs.python.org/3/library/sqlite3.html), [Psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html) e [PostgreSQL nos testes do GitHub](https://docs.github.com/en/actions/tutorials/use-containerized-services/create-postgresql-service-containers).
