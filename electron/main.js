const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let flaskProcess;
let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    icon: path.join(__dirname, 'icon.png'),
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    }
  });

  // Abre o frontend servido pelo Flask
  mainWindow.loadURL('http://127.0.0.1:5000');

  mainWindow.on('closed', () => {
    mainWindow = null;
    if (flaskProcess) flaskProcess.kill();
  });
}

// Inicia Flask antes do Electron carregar
app.whenReady().then(() => {
  const backendPath = path.join(__dirname, '..', 'backend', 'app.py');
  flaskProcess = spawn('python', [backendPath], { stdio: 'inherit' });
  console.log('🔹 Flask iniciado...');

  // Aguarda alguns segundos antes de abrir a janela
  setTimeout(createWindow, 3000);
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
  if (flaskProcess) flaskProcess.kill();
});
