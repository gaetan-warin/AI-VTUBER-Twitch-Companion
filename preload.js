const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electron', {
    send: (channel, data) => ipcRenderer.send(channel, data),
    receive: (channel, func) => ipcRenderer.on(channel, (event, ...args) => func(...args)),
    getScreenSources: async () => {
        try {
            return await ipcRenderer.invoke('get-sources');
        } catch (error) {
            console.error('Failed to get screen sources:', error);
            throw error;
        }
    }
});
