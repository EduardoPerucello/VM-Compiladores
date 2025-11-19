const BACKEND = "http://127.0.0.1:5000";

const editor = document.getElementById('editor');
const btnLoad = document.getElementById('btnLoad');
const btnStep = document.getElementById('btnStep');
const btnRun = document.getElementById('btnRun');
const btnReset = document.getElementById('btnReset');
const btnUpload = document.getElementById('btnUpload');
const fileInput = document.getElementById('fileInput');

const pcEl = document.getElementById('pc');
const nextEl = document.getElementById('next_instr');
const stackView = document.getElementById('stackView');
const memView = document.getElementById('memView');
const outView = document.getElementById('outView');
const logView = document.getElementById('logView');
const exampleSelect = document.getElementById('exampleSelect');
const btnLoadExample = document.getElementById('btnLoadExample');

async function api(path, opts = {}) {
  const res = await fetch(BACKEND + path, opts);
  return res.json();
}

function log(msg) {
  const now = new Date().toLocaleTimeString();
  logView.textContent = `[${now}] ${msg}\n` + logView.textContent;
}

async function loadExamples() {
  const ex = await api('/examples');
  exampleSelect.innerHTML = '';
  Object.keys(ex).forEach(k => {
    const o = document.createElement('option');
    o.value = k;
    o.textContent = k;
    exampleSelect.appendChild(o);
  });
  window.examples = ex;
}

async function loadProgram() {
  const asm = editor.value;
  const r = await api('/load', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ asm })
  });
  if (r.status === 'ok') {
    log('Programa carregado.');
    updateState();
  } else {
    log('Erro ao carregar: ' + r.message);
  }
}

// ------------------------
// UPLOAD DE ARQUIVO
// ------------------------
btnUpload.onclick = async () => {
  if (fileInput.files.length === 0) {
    alert("Escolha um arquivo!");
    return;
  }

  let file = fileInput.files[0];
  let text = await file.text();

  const r = await api("/upload_program", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ program: text })
  });

  if (r.status === "ok") {
    editor.value = text;
    log("Arquivo carregado com sucesso.");
    updateState();
  } else {
    log("Erro ao carregar arquivo: " + r.error);
  }
};

// ------------------------
// STEP
// ------------------------
async function step() {
  const r = await api('/step', { method: 'POST' });

  if (r.status === 'error' &&
      r.message.toLowerCase().includes('rd attempted')) {

    const val = await window.electronAPI.askInput("Digite um valor para RD:");

    if (val !== null) {
      await api('/input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: val })
      });

      const again = await api('/step', { method: 'POST' });
      updateFromSnapshot(again.snapshot);
      return;
    }
  }

  updateFromSnapshot(r.snapshot);
}

// ------------------------
// RUN
// ------------------------
async function run() {
  const r = await api('/run', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({ limit: 1000000 })
  });

  if (r.status === 'error' &&
      r.message.toLowerCase().includes('rd attempted')) {

    const val = await window.electronAPI.askInput("Digite um valor para RD:");

    if (val !== null) {
      await api('/input', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ value: val })
      });

      const again = await api('/run', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ limit: 1000000 })
      });

      updateFromSnapshot(again.snapshot);
      return;
    }
  }

  updateFromSnapshot(r.snapshot);
}

// ------------------------
async function reset() {
  const r = await api('/reset', { method: 'POST' });
  updateFromSnapshot(r.snapshot);
}

async function updateState() {
  const s = await api('/state');
  updateFromSnapshot(s);
}

function updateFromSnapshot(snap) {
  if (!snap) return;
  pcEl.textContent = snap.pc;
  nextEl.textContent = snap.next_instr;
  stackView.textContent = JSON.stringify(snap.stack, null, 2);
  memView.textContent = JSON.stringify(snap.mem, null, 2);
  outView.textContent = JSON.stringify(snap.output, null, 2);
  document.getElementById("status").textContent =
    snap.halted ? "halted" : "running";

  if (snap.last_error) log("Erro: " + snap.last_error);
}

btnLoad.addEventListener('click', loadProgram);
btnStep.addEventListener('click', step);
btnRun.addEventListener('click', run);
btnReset.addEventListener('click', reset);

btnLoadExample.addEventListener('click', () => {
  const k = exampleSelect.value;
  editor.value = window.examples[k];
});

window.addEventListener('load', () => {
  loadExamples();
  updateState();
});
