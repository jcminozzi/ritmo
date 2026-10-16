# Ritmo

**Um chatbot financeiro para consultar despesas, comparar meses e conferir os números.**

Faça uma pergunta em português e receba valores calculados, um gráfico e a fonte usada na resposta. Funciona localmente com CSV ou SQLite e tem um adaptador opcional para PostgreSQL.

![Resultados reais da demonstração local do chatbot financeiro Ritmo](examples/preview.png)

*Composição visual com respostas e valores realmente gerados pelo programa. Dados fictícios. Não é captura da interface web; a revisão visual da tela no navegador ainda está pendente nesta entrega.*

## Experimentar em um minuto

Python 3.11 ou superior. Na pasta do projeto:

```powershell
python app.py
```

Abra o endereço mostrado no terminal, normalmente `http://127.0.0.1:4321/`. A tela tem chat, cartões de despesas pagas e pendentes, gráficos, conferência da fonte e importação de outro CSV. Não precisa instalar pacotes, cadastrar uma API ou configurar um banco para essa demonstração.

Se preferir o terminal:

```powershell
python bot.py demo
python bot.py chat
```

## Quem usaria

Uma pessoa da área administrativa ou financeira que precisa conferir despesas antes de uma reunião. A demonstração evita procurar e somar linhas manualmente: mostra o total pago, categorias, evolução por mês e maiores lançamentos.

| Pergunta | O que o chatbot entrega |
|---|---|
| Quanto gastamos em fevereiro de 2026? | Total pago, quantidade de lançamentos e pendências separadas |
| Mostre os gastos por categoria | Lista e gráfico das categorias |
| Compare os gastos por mês | Totais mensais e diferença entre os dois últimos meses disponíveis |
| Quais foram as maiores despesas? | Até cinco lançamentos, com fornecedor e valor |
| Há erros na planilha? | Linhas separadas para revisão no importador CSV |

Use mês e ano, como `2026-02`, ou o nome do mês com ano. Nomes exatos de categorias da base também podem filtrar. Cada pergunta é independente. Exclusões, intervalos de dias e filtros por fornecedor ainda não são suportados; nesses casos a aplicação pede reformulação quando reconhece o padrão.

## A IA foi treinada aqui?

Sim, **o classificador de intenções é treinado neste projeto**, com implementação didática de Naive Bayes multinomial em Python. Ele aprende pesos de palavras e pares de palavras a partir de perguntas rotuladas. Não usa um modelo de linguagem pronto nem uma API de IA.

O alcance é específico: reconhecer seis tipos de intenção. Ele não produz texto livre; as respostas usam textos definidos no programa e números calculados em SQL. Não deve ser apresentado como um ChatGPT próprio. Um modelo generativo é uma possível evolução, com outra avaliação e outro escopo.

```text
Pergunta → classificador treinado → consulta conhecida → números + resposta + gráfico
```

```powershell
python train.py
python train.py --check
```

São 90 exemplos sintéticos de treino e 30 de validação separados, escritos com assistência de IA. O conjunto de validação foi consultado durante o desenvolvimento; não é teste externo intocado. A versão atual acertou **25 de 30 perguntas (83,3%)** e se absteve em cinco. Esse resultado pequeno não mede desempenho com funcionários ou bases de empresas. [Veja as previsões, os erros e o histórico](examples/evaluation.md).

O limiar de margem do classificador é uma heurística, sem probabilidade calibrada. Em perguntas que não reconhece, o chatbot apresenta seu alcance e exemplos. A extração dos filtros de mês e categoria usa regras explícitas, separadas do modelo.

## Conectar outras fontes

```powershell
python connect.py outputs/demo.db
python app.py --source sqlite --input outputs/demo.db
```

Para PostgreSQL, configure a conexão no ambiente local e use:

```powershell
python -m pip install -r requirements-postgres.txt
python app.py --source postgres
```

O adaptador usa `RITMO_DATABASE_URL` e uma tabela ou view `finance_expenses`. Cada empresa precisa mapear suas colunas para esse contrato. O acesso do chatbot é de leitura e as consultas são fixas e parametrizadas. Credenciais não entram no navegador ou no código. [Guia de conexão e formato da base](docs/conexoes.md).

CSV e SQLite são exercitados nos testes locais. O CI inclui um PostgreSQL descartável, com dados fictícios, para verificar consultas e bloqueio de escrita. Nenhum banco de empresa foi acessado. MySQL, SQL Server e ERPs ainda não têm adaptadores.

## Dados e conferência

A base fictícia inclui 36 lançamentos válidos e três linhas problemáticas. Valores são calculados em centavos inteiros. Gastos consideram somente o status `pago`; `pendente` fica separado. Não há previsão de lucro, análise tributária ou recomendação de investimento.

Cada resposta numérica informa a fonte, o recorte, o horário da consulta e uma amostra de IDs. Essa amostra ajuda a conferir registros, mas não lista todas as linhas somadas. A conexão SQL confere a estrutura da view; a limpeza linha a linha é do importador CSV.

Os gráficos limitam categorias a oito e meses a 12; maiores despesas mostram até cinco linhas. A comparação entre meses pode incluir períodos incompletos e não atribui causas às variações.

## Testes e estrutura

```powershell
python -m unittest discover -s tests -v
```

- `intent_model.py` e `train.py`: aprendizado e avaliação reproduzível.
- `data_sources.py`: CSV, SQLite e PostgreSQL.
- `finance_bot.py`: filtros, consultas e respostas.
- `app.py` e `web/`: API e interface local.
- `docs/`: contrato para integrar dados de outra base.
- `examples/`: respostas reais e avaliação do classificador.

Os testes cobrem cálculos, filtros, duplicatas, falhas de importação, leitura sem escrita, API HTTP e isolamento de arquivos. O teste PostgreSQL é pulado localmente quando não há banco de teste configurado; o workflow o executa em uma instância descartável.

O servidor é para uso local, em `127.0.0.1`, sem autenticação ou implantação pública. A interface teve verificação de estrutura e sintaxe; o ambiente de desenvolvimento bloqueou a navegação local e sua revisão visual continua pendente. Os testes HTTP são executados no GitHub Actions.

Projeto pessoal de João Carlos Minozzi, construído com assistência de IA para estudo e portfólio de estágio. O próximo passo de aprendizado é ampliar e revisar as perguntas com pessoas reais, investigar as abstenções e estudar outro classificador.

Referências: [Naive Bayes](https://scikit-learn.org/stable/modules/naive_bayes.html), [sqlite3](https://docs.python.org/3/library/sqlite3.html), [Psycopg](https://www.psycopg.org/psycopg3/docs/basic/transactions.html).
