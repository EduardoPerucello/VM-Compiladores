// frontend/main.js
const editor = document.getElementById('editor');
const btnLoad = document.getElementById('btnLoad');
const btnStep = document.getElementById('btnStep');
const btnRun = document.getElementById('btnRun');
const btnReset = document.getElementById('btnReset');
const pcEl = document.getElementById('pc');
const nextEl = document.getElementById('next_instr');
const stackView = document.getElementById('stackView');
const memView = document.getElementById('memView');
const outView = document.getElementById('outView');
const logView = document.getElementById('logView');
const exampleSelect = document.getElementById('exampleSelect');
const btnLoadExample = document.getElementById('btnLoadExample');

const API = '';

async function api(path, opts) {
  const res = await fetch(path, opts);
  return res.json();
}

async function loadExamples() {
  try {
    const ex = await api('/examples');
    exampleSelect.innerHTML = '';
    Object.keys(ex).forEach(k => {
      const o = document.createElement('option');
      o.value = k;
      o.textContent = k;
      exampleSelect.appendChild(o);
    });
    window.examples = ex;
    log('Exemplos carregados.');
  } catch (e) {
    log('Erro ao carregar exemplos: ' + e);
  }
}

async function loadProgram() {
  const asm = editor.value;
  try {
    const r = await api('/load', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ asm })
    });
    if (r.status === 'ok') {
      log('Programa carregado. Instruções: ' + r.prog_len);
      updateState();
    } else {
      log('Erro ao carregar: ' + JSON.stringify(r));
    }
  } catch (e) {
    log('Erro load: ' + e);
  }
}

async function step() {
  try {
    const r = await api('/step', { method: 'POST' });
    console.log("Resposta do /step:", r); 

    // 🔹 Detecta se o erro foi de RD sem valor na fila
    if (r.status === 'error' && r.message &&
        r.message.toLowerCase().includes('rd attempted but input queue empty')) {
      const val = prompt('Digite um valor para RD:');
      if (val !== null) {
        await api('/input', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ value: val })
        });
        const next = await api('/step', { method: 'POST' });
        updateFromSnapshot(next.snapshot);
        log(`Valor ${val} lido para RD.`);
        return;
      } else {
        log('Execução pausada — RD aguardando valor.');
        return;
      }
    }

    if (r.status === 'ok' || r.status === 'halted') {
      updateFromSnapshot(r.snapshot);
      if (r.status === 'halted') log('Execução finalizada.');
    } else {
      updateState();
    }

  } catch (e) {
    log('Erro step: ' + e);
  }
}

async function run() {
  try {
    const r = await api('/run', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ limit: 1000000 })
    });

    // 🔹 Detecta se o erro foi de RD sem valor na fila
    if (r.status === 'error' && r.message &&
        r.message.toLowerCase().includes('rd attempted but input queue empty')) {
      const val = prompt('Digite um valor para RD:');
      if (val !== null) {
        await api('/input', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ value: val })
        });
        // Continua automaticamente a execução
        const again = await api('/run', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({ limit: 1000000 })
        });
        updateFromSnapshot(again.snapshot);
        log(`Valor ${val} lido para RD (execução retomada).`);
        return;
      } else {
        log('Execução pausada — RD aguardando valor.');
        return;
      }
    }

    updateFromSnapshot(r.snapshot);
    if (r.status === 'halted' || r.snapshot?.halted) log('Execução finalizada.');
  } catch (e) {
    log('Erro run: ' + e);
  }
}

async function reset() {
  try {
    const r = await api('/reset', { method: 'POST' });
    updateFromSnapshot(r.snapshot);
    log('VM resetada.');
  } catch (e) {
    log('Erro reset: ' + e);
  }
}

async function updateState() {
  try {
    const s = await api('/state');
    updateFromSnapshot(s);
  } catch (e) {
    log('Erro state: ' + e);
  }
}

function updateFromSnapshot(snap) {
  if (!snap) return;
  pcEl.textContent = snap.pc ?? '-';
  nextEl.textContent = snap.next_instr || '-';
  stackView.textContent = JSON.stringify(snap.stack || [], null, 2);
  memView.textContent = JSON.stringify(snap.mem || {}, null, 2);
  outView.textContent = JSON.stringify(snap.output || [], null, 2);

  if (snap.halted) {
    document.getElementById('status').textContent =
      snap.last_error ? ('halted: ' + snap.last_error) : 'halted';
  } else {
    document.getElementById('status').textContent = 'running';
  }

  if (snap.last_error) {
    log('Erro: ' + snap.last_error);
  }
}

function log(msg) {
  const now = new Date().toLocaleTimeString();
  logView.textContent = `[${now}] ${msg}\n` + logView.textContent;
}

// --- Eventos ---
btnLoad.addEventListener('click', loadProgram);
btnStep.addEventListener('click', step);
btnRun.addEventListener('click', run);
btnReset.addEventListener('click', reset);
btnLoadExample.addEventListener('click', () => {
  const k = exampleSelect.value;
  if (window.examples && window.examples[k]) {
    editor.value = window.examples[k];
    log(`Exemplo "${k}" carregado no editor.`);
  }
});

window.addEventListener('load', () => {
  loadExamples();
  updateState();
  setInterval(updateState, 1500);
});
