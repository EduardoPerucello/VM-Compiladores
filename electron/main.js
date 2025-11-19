const { app, BrowserWindow, ipcMain, dialog } = require("electron");
const { spawn } = require("child_process");
const path = require("path");

let backend;

// 🔹 POP-UP DE INPUT PARA RD
ipcMain.handle("ask-input", async (_, message) => {
  return new Promise((resolve) => {

    const win = new BrowserWindow({
      width: 400,
      height: 200,
      modal: true,
      parent: BrowserWindow.getFocusedWindow(),
      webPreferences: {
        nodeIntegration: true,
        contextIsolation: false
      }
    });

    win.loadFile(path.join(__dirname, "inputWindow.html"));

    win.webContents.on("did-finish-load", () => {
      win.webContents.send("set-message", message);
    });

    ipcMain.once("input-value", (_, value) => {
      resolve(value);
    });
  });
});


function startBackend() {
  const exePath = app.isPackaged
    ? path.join(process.resourcesPath, "backend", "app.exe")
    : path.join(__dirname, "..", "backend", "app.exe");

  console.log("Iniciando backend:", exePath);

  backend = spawn(exePath, [], {
    cwd: path.dirname(exePath),
    detached: true,
    stdio: "ignore",
  });

  backend.unref();
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  const indexPath = app.isPackaged
    ? `file://${path.join(process.resourcesPath, "frontend", "index.html")}`
    : `file://${path.join(__dirname, "..", "frontend", "index.html")}`;

  win.loadURL(indexPath);
}

app.whenReady().then(() => {
  startBackend();
  setTimeout(createWindow, 1000);
});

app.on("window-all-closed", () => {
  app.quit();
});
