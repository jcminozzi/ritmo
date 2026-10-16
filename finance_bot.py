"""Pergunta → intenção aprendida → consulta SQL conhecida → resposta e gráfico."""
from pathlib import Path
import re
from intent_model import IntentModel, normalize

ROOT=Path(__file__).resolve().parent
MONTHS=('janeiro','fevereiro','marco','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro')
HELP='Posso consultar despesas pagas: total, categorias, evolução por mês, maiores despesas e qualidade do CSV. Experimente: “Quanto gastamos em fevereiro de 2026?”'


def brl(cents):
    value=int(cents or 0)
    whole, decimal=divmod(abs(value),100)
    return ('-' if value<0 else '')+'R$ '+f'{whole:,}'.replace(',','.')+f',{decimal:02d}'


def month_filters(question, years):
    normalized=normalize(question)
    iso=re.findall(r'\b\d{4}-\d{2}\b',normalized)
    if iso:
        if any(not re.fullmatch(r'\d{4}-(0[1-9]|1[0-2])',m) for m in iso):
            raise ValueError('Use um mês válido, como 2026-02.')
        return sorted(set(iso))
    selected=[i+1 for i,name in enumerate(MONTHS) if re.search(r'\b'+name+r'\b',normalized)]
    explicit_years=sorted(set(re.findall(r'\b20\d{2}\b',normalized)))
    if selected:
        choices=explicit_years or years
        if len(choices)!=1:
            raise ValueError('Informe o mês e o ano, como 2026-02.')
        return [f'{choices[0]}-{m:02d}' for m in selected]
    if explicit_years:
        raise ValueError('Esta versão filtra por mês. Informe, por exemplo, 2026-02.')
    if re.search(r'\b(hoje|ontem|atual|nesse|neste|passado)\b',normalized):
        raise ValueError('Informe o período com mês e ano, como 2026-02.')
    return []


class FinanceBot:
    def __init__(self,source,model=None):
        self.source=source
        self.model=model or IntentModel.load(ROOT/'model/intent-model.json')

    def overview(self):
        return self.source.snapshot()

    def ask(self,question):
        if not isinstance(question,str) or not question.strip() or len(question)>500:
            return {'kind':'clarify','text':'Escreva uma pergunta de até 500 caracteres.','chart':[]}
        prediction=self.model.predict(question)
        intent=prediction['intent']
        if intent in ('other','unclear'):
            return {'kind':'clarify','intent':intent,'text':HELP,'chart':[]}
        normalized=normalize(question)
        if (re.search(r'\b(nao|exceto|exclua|tirando|dia|dias)\b',normalized)
                or re.search(r'\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}',normalized)):
            return {'kind':'clarify','intent':intent,'text':'Esta versão aceita filtros de mês e ano e nomes de categorias. Reformule sem exclusões ou intervalos de dias.','chart':[]}
        if 'fornecedor' in normalized and intent!='largest':
            return {'kind':'clarify','intent':intent,'text':'Ainda não filtro por fornecedor. Posso mostrar as maiores despesas com seus fornecedores.','chart':[]}
        first=self.source.snapshot()
        try:
            filters=month_filters(question,first['years'])
        except ValueError as error:
            return {'kind':'clarify','intent':intent,'text':str(error),'chart':[]}
        categories=[c for c in first['available_categories'] if re.search(r'\b'+re.escape(normalize(c))+r'\b',normalized)]
        data=self.source.snapshot(filters,categories) if filters or categories else first
        scope=', '.join(filters) if filters else 'todos os períodos da fonte'
        if categories:scope+=' · categorias: '+', '.join(categories)
        summary=data['summary']
        result={'kind':'answer','intent':intent,'scope':scope,'chart':[],
                'evidence':{'source':data['source'],'sample_ids':data['sample_ids'],
                            'queried_at':data['queried_at'],'scope':scope,
                            'rule':'Somente status pago entra nos gastos; pendências ficam separadas.'}}
        if intent=='quality':
            if data['issues'] is None:
                result['text']='A estrutura da fonte SQL foi conferida. Esta conexão não executa as regras de limpeza do importador CSV.'
            else:
                result['text']=f"O CSV contém {len(data['issues'])} linhas separadas para revisão. A base válida tem {summary['records']} lançamentos neste recorte."
                result['issues']=data['issues']
            return result
        if not summary['paid_count']:
            result['text']='Não encontrei despesas pagas para '+scope+'. Isso indica ausência de registros nesse recorte, não uma previsão.'
            return result
        if intent=='total':
            result['text']=f"As despesas pagas somam {brl(summary['paid_cents'])}, em {summary['paid_count']} lançamentos, considerando {scope}. Há também {brl(summary['pending_cents'])} pendentes, fora desse total."
            result['chart']=[{'label':'Pago','cents':summary['paid_cents']},{'label':'Pendente','cents':summary['pending_cents']}]
        elif intent=='categories':
            result['text']='Despesas pagas por categoria (até oito), considerando '+scope+':\n'+'\n'.join(r['label']+': '+brl(r['cents']) for r in data['categories'])
            result['chart']=data['categories']
        elif intent=='months':
            result['text']='Despesas pagas por mês (até 12 meses disponíveis):\n'+'\n'.join(r['label']+': '+brl(r['cents']) for r in data['months'])
            result['chart']=data['months']
            if len(data['months'])>=2:
                previous,current=data['months'][-2:]
                difference=current['cents']-previous['cents']
                direction='aumento' if difference>=0 else 'redução'
                result['text']+=f"\nEntre {previous['label']} e {current['label']}, houve {direction} de {brl(abs(difference))}. Os períodos podem estar incompletos; o bot não atribui uma causa."
        elif intent=='largest':
            result['text']='Maiores despesas pagas (até cinco), considerando '+scope+':\n'+'\n'.join(f"{r['expense_id']} · {r['supplier']} · {brl(r['amount_cents'])}" for r in data['largest'])
            result['chart']=[{'label':r['supplier'],'cents':r['amount_cents']} for r in data['largest']]
        return result
