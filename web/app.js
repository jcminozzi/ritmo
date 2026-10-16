const money = cents => new Intl.NumberFormat('pt-BR', {style:'currency',currency:'BRL'}).format(Number(cents || 0)/100);
const chatLog = document.querySelector('#chat-log');
const question = document.querySelector('#pergunta');
const sendButton = document.querySelector('#send');
let busy = false;
async function api(path, payload) {
  const response = await fetch(path, payload === undefined ? {} : {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Não foi possível consultar a fonte.');
  return data;
}
function message(speaker, text) {
  const article = document.createElement('article');
  article.className = 'message ' + (speaker === 'VOCÊ' ? 'user' : 'assistant');
  const label = document.createElement('span');
  label.className = 'speaker'; label.textContent = speaker;
  const paragraph = document.createElement('p'); paragraph.textContent = text;
  article.append(label, paragraph); chatLog.append(article); chatLog.scrollTop = chatLog.scrollHeight;
}
function drawChart(rows, title) {
  const target = document.querySelector('#chart'); target.replaceChildren();
  document.querySelector('#chart-title').textContent = title;
  const maximum = Math.max(1, ...rows.map(row => Number(row.cents)));
  for (const row of rows) {
    const item = document.createElement('div'); item.className = 'chart-row';
    const header = document.createElement('div');
    const label = document.createElement('span'); label.textContent = row.label;
    const value = document.createElement('strong'); value.textContent = money(row.cents);
    header.append(label, value);
    const track = document.createElement('div'); track.className = 'chart-track';
    const bar = document.createElement('div'); bar.className = 'chart-bar';
    bar.style.width = Math.max(0, Math.min(100, Number(row.cents)/maximum*100)) + '%';
    track.append(bar); item.append(header, track); target.append(item);
  }
  if (!rows.length) target.textContent = 'Sem valores para desenhar neste recorte.';
}
function overview(data) {
  document.querySelector('#paid').textContent = money(data.summary.paid_cents);
  document.querySelector('#pending').textContent = money(data.summary.pending_cents);
  document.querySelector('#records').textContent = data.summary.records;
  document.querySelector('#quality').textContent = data.issues === null ? 'Fonte SQL · leitura direta' : `${data.issues.length} linhas para revisão`;
  document.querySelector('#source-badge').textContent = data.demo ? 'Demonstração · dados fictícios' : 'Fonte selecionada · leitura local';
  document.querySelector('#source-name').textContent = data.source;
  document.querySelector('#source-info').textContent = data.demo ? 'A base inicial tem despesas fictícias e linhas com problemas para praticar conferência.' : 'A fonte está ativa. Cada pergunta consulta os dados disponíveis no momento.';
  drawChart(data.categories, 'Despesas pagas por categoria');
  document.querySelector('#chart-note').textContent = 'Indicadores do conjunto completo. Uma pergunta pode selecionar outro período no gráfico.';
}
async function ask(text) {
  if (busy || !text.trim()) return;
  busy = true; sendButton.disabled = true; question.disabled = true;
  message('VOCÊ', text); question.value = '';
  try {
    const data = await api('/api/chat', {question:text});
    message('RITMO', data.text);
    if (data.chart.length) {
      drawChart(data.chart, {total:'Pago e pendente',categories:'Despesas por categoria',months:'Despesas por mês',largest:'Maiores despesas'}[data.intent] || 'Resultado');
      document.querySelector('#chart-note').textContent = `Recorte: ${data.scope}. Os cartões no topo continuam mostrando o conjunto completo.`;
    }
    if (data.evidence) {
      const e = data.evidence;
      document.querySelector('#evidence').textContent = `Fonte: ${e.source}\nPeríodo: ${e.scope}\n${e.rule}\nExemplos de IDs: ${e.sample_ids.join(', ') || 'nenhum'}\nConsultado em: ${new Date(e.queried_at).toLocaleString('pt-BR')}`;
    }
  } catch (error) { message('RITMO', error.message); }
  finally { busy = false; sendButton.disabled = false; question.disabled = false; question.focus(); }
}
document.querySelector('#chat-form').addEventListener('submit', event => {event.preventDefault(); ask(question.value);});
document.querySelectorAll('#suggestions button').forEach(button => button.addEventListener('click', () => ask(button.textContent)));
document.querySelector('#csv-file').addEventListener('change', async event => {
  const file = event.target.files[0]; if (!file) return;
  const status = document.querySelector('#upload-status');
  if (busy) {status.textContent='Aguarde a consulta terminar para trocar a fonte.'; event.target.value=''; return;}
  if (file.size>1_000_000) {status.textContent='Selecione um CSV de até 1 MB.'; event.target.value=''; return;}
  busy = true; sendButton.disabled = true; status.textContent = 'Conferindo o CSV…';
  try {
    const data = await api('/api/data', {name:file.name,content:await file.text()});
    overview(data); chatLog.replaceChildren();
    message('RITMO', 'Fonte atualizada. As próximas perguntas usam o CSV selecionado.');
    document.querySelector('#evidence').textContent = 'Faça uma pergunta para conferir a fonte e o recorte.';
    status.textContent = 'CSV carregado nesta sessão. O arquivo original continua no seu computador.';
  } catch (error) {status.textContent=error.message;}
  finally {busy=false; sendButton.disabled=false; event.target.value='';}
});
api('/api/overview').then(overview).catch(error => {
  document.querySelector('#source-badge').textContent = 'Fonte indisponível';
  message('RITMO', error.message);
});
