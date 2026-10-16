"""Treina o classificador e mede o resultado em um conjunto sintético separado."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from intent_model import IntentModel, normalize

ROOT=Path(__file__).resolve().parent


def evaluate(model, cases):
    predictions=[]
    for case in cases:
        prediction=model.predict(case['question'])
        predictions.append({**case,'predicted':prediction['intent'],'raw_predicted':prediction['raw_intent']})
    labels=sorted({case['intent'] for case in cases})
    scores=[]
    for label in labels:
        tp=sum(p['intent']==label and p['predicted']==label for p in predictions)
        fp=sum(p['intent']!=label and p['predicted']==label for p in predictions)
        fn=sum(p['intent']==label and p['predicted']!=label for p in predictions)
        scores.append(2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0)
    n=len(cases)
    correct=sum(p['intent']==p['predicted'] for p in predictions)
    return {'dataset':'sintético, pequeno, escrito para estudo; não mede desempenho em empresas',
            'test_examples':n, 'correct':correct,'accuracy':correct/n,
            'macro_f1':sum(scores)/len(scores),
            'coverage':sum(p['predicted']!='unclear' for p in predictions)/n,
            'majority_baseline':max(Counter(c['intent'] for c in cases).values())/n,
            'predictions':predictions}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check',action='store_true',help='verificar artefatos versionados sem reescrever')
    args=parser.parse_args()
    train=json.loads((ROOT/'data/train.json').read_text(encoding='utf-8'))
    test=json.loads((ROOT/'data/test.json').read_text(encoding='utf-8'))
    if {normalize(r['question']) for r in train}&{normalize(r['question']) for r in test}:
        raise ValueError('Treino e teste têm perguntas repetidas.')
    model=IntentModel.train(train)
    report=evaluate(model,test)
    report['training_examples']=len(train)
    report['dataset_sha256']={name:hashlib.sha256((ROOT/f'data/{name}.json').read_bytes()).hexdigest() for name in ('train','test')}
    if args.check:
        if model.data!=IntentModel.load(ROOT/'model/intent-model.json').data:
            raise ValueError('Modelo desatualizado; execute python train.py.')
        if report!=json.loads((ROOT/'examples/evaluation.json').read_text(encoding='utf-8')):
            raise ValueError('Avaliação desatualizada; execute python train.py.')
    else:
        model.save(ROOT/'model/intent-model.json')
        (ROOT/'examples/evaluation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        lines=['# Avaliação do classificador de intenções','',
               f"Treino: {len(train)} perguntas sintéticas. Teste separado: {len(test)} perguntas sintéticas.",
               f"Acertos: {report['correct']}/{len(test)}. Acurácia: {report['accuracy']:.1%}. Macro F1: {report['macro_f1']:.3f}.",
               f"Cobertura: {report['coverage']:.1%}. Baseline da classe majoritária: {report['majority_baseline']:.1%}.",'',
               'O conjunto é pequeno e foi escrito com assistência de IA. Perguntas parecidas podem inflar o resultado. Ele foi consultado durante o desenvolvimento: não é teste externo intocado, avaliação com usuários reais nem prova de prontidão para empresas.',
               'Primeira versão: 22/30 acertos. Uma falha na pergunta da demonstração motivou duas revisões: preservar a palavra “quanto” como sinal da intenção e tratar nomes de meses somente como filtros. O resultado atual reflete essas revisões.',
               'A margem de abstenção foi definida em 0,6 antes da primeira avaliação. Não é probabilidade calibrada.','',
               '## Erros e abstenções','']
        lines += [f"- {p['question']} | esperado: {p['intent']} | previsto: {p['predicted']}" for p in report['predictions'] if p['intent']!=p['predicted']]
        (ROOT/'examples/evaluation.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ('predictions','dataset_sha256')},ensure_ascii=True))


if __name__=='__main__':main()
