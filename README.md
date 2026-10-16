# Ritmo

**Um bot para a equipe comercial consultar o relatório de vendas sem abrir uma planilha.**

O Ritmo lê o relatório produzido pelo [Pulso](https://github.com/jcminozzi/pulso) e responde a comandos curtos: receita, pedidos, categorias e qualidade dos dados. É um projeto de estudo para estágio, com um caso de uso simples e dados fictícios.

![Respostas reais da demonstração local do Ritmo](examples/preview.png)

*Imagem montada com as respostas reais do modo local; não é uma captura do Telegram. Dados fictícios.*

## Como seria usado

1. Uma pessoa da equipe exporta a planilha e roda o Pulso.
2. O Pulso gera `report.json` com os indicadores conferidos.
3. O bot consulta esse arquivo e responde aos comandos da conversa autorizada.

## Experimentar no computador

Python 3.11 ou superior. Sem pacotes adicionais e sem token.

```powershell
python bot.py demo
python -m unittest discover -s tests -v
```

A demonstração é uma conversa local no terminal. Não envia mensagens a ninguém. Uma transcrição está em `examples/conversation.txt`.

## Comandos

| Comando | Resultado |
|---|---|
| /vendas | Receita, pedidos, ticket médio e cancelamentos |
| /categorias | Receita por categoria |
| /resumo | Leitura simples dos resultados |
| /qualidade | Quantidade de linhas válidas e para revisão |
| /ajuda | Lista de comandos |

## Usar um relatório diferente

```powershell
python bot.py demo --report CAMINHO_DO_REPORT_JSON
```

Se o Pulso tiver gerado um rascunho de IA, o bot pode exibi-lo em `/resumo` usando `--notes CAMINHO_DO_AI_NOTES_JSON`. O Ritmo não chama um modelo nem refaz os cálculos.

## Integração opcional com Telegram

Crie um bot no BotFather e configure `TELEGRAM_BOT_TOKEN` no ambiente. Informe o ID numérico da sua conversa privada:

```powershell
python bot.py telegram --chat-id SEU_ID_NUMERICO --report CAMINHO_DO_REPORT_JSON
```

Os marcadores em letras maiúsculas precisam ser substituídos pelos valores locais. O runner usa `getUpdates` e `sendMessage`, aceita somente a conversa privada configurada e salva o offset em SQLite. O ID aparece em `message.chat.id` na resposta de `getUpdates`, conforme a documentação oficial. Não publique seu token. Arquivos `.env` não são carregados automaticamente.

A integração foi testada com respostas simuladas. Não houve ativação de bot nem envio real de mensagens nesta entrega. Não há hospedagem, atualização automática da planilha ou garantia de entrega exatamente uma vez. A intenção é praticar funções, JSON, APIs, consultas a um relatório e tratamento de erros.

Projeto pessoal de João Carlos Minozzi, construído com assistência de IA para estudo e portfólio de estágio. Não representa implantação em empresa.

Referência: [Telegram Bot API](https://core.telegram.org/bots/api).
