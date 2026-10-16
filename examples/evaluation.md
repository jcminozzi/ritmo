# Avaliação do classificador de intenções

Treino: 90 perguntas sintéticas. Teste separado: 30 perguntas sintéticas.
Acertos: 25/30. Acurácia: 83.3%. Macro F1: 0.887.
Cobertura: 83.3%. Baseline da classe majoritária: 16.7%.

O conjunto é pequeno e foi escrito com assistência de IA. Perguntas parecidas podem inflar o resultado. Ele foi consultado durante o desenvolvimento: não é teste externo intocado, avaliação com usuários reais nem prova de prontidão para empresas.
Primeira versão: 22/30 acertos. Uma falha na pergunta da demonstração motivou duas revisões: preservar a palavra “quanto” como sinal da intenção e tratar nomes de meses somente como filtros. O resultado atual reflete essas revisões.
A margem de abstenção foi definida em 0,6 antes da primeira avaliação. Não é probabilidade calibrada.

## Erros e abstenções

- Me passa a soma dos pagamentos. | esperado: total | previsto: unclear
- Qual o valor acumulado das despesas pagas? | esperado: total | previsto: unclear
- Vai chover no fim de semana? | esperado: other | previsto: unclear
- Pode redigir uma petição? | esperado: other | previsto: unclear
- Qual o resultado da partida de futebol? | esperado: other | previsto: unclear
