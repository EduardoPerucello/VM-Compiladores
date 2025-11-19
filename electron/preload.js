const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("electronAPI", {
  askInput: (msg) => ipcRenderer.invoke("ask-input", msg)
});
