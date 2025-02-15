const { app, BrowserWindow, ipcMain, desktopCapturer } = require('electron');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let speechProcess;

async function startSpeechServer() {
    speechProcess = exec('node speechServer.js', async (error, stdout, stderr) => {
        if (error) return console.error(`Speech server error: ${error.message}`);;
        if (stderr) console.error(`Speech stderr: ${stderr}`);
        console.log(`Speech stdout: ${stdout}`);
    });
}

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1200,
        height: 800,
        webPreferences: {
            preload: path.join(__dirname, 'preload.js'),
            contextIsolation: true,
            enableRemoteModule: false,
            nodeIntegration: false,
            webSecurity: true,
            media: true
        }
    });

    // Add screen capture permissions
    mainWindow.webContents.session.setPermissionCheckHandler((webContents, permission, requestingOrigin, details) => {
        return permission === 'media' || permission === 'screen';
    });

    mainWindow.webContents.session.setPermissionRequestHandler((webContents, permission, callback, details) => {
        return callback(permission === 'media' || permission === 'screen');
    });

    mainWindow.loadURL('http://localhost:5000');

    mainWindow.on('closed', function () {
        mainWindow = null;
    });
}

// Add screen capture handlers
ipcMain.handle('get-sources', async () => {
    try {
        const sources = await desktopCapturer.getSources({
            types: ['window', 'screen'],
            thumbnailSize: { width: 150, height: 150 },
            fetchWindowIcons: true
        });

        // Sort sources to put displays first
        return sources.sort((a, b) => {
            const aIsDisplay = a.name.includes('Screen') || a.name.includes('Display');
            const bIsDisplay = b.name.includes('Screen') || b.name.includes('Display');
            return bIsDisplay - aIsDisplay;
        });
    } catch (error) {
        console.error('Error getting sources:', error);
        throw error;
    }
});

app.on('ready', async () => {
    try {
        // Start speech server first
        await startSpeechServer();

        // Then create window and start Flask
        createWindow();

        // Start the Flask server
        const flaskProcess = exec('python app.py', (error, stdout, stderr) => {
            if (error) console.error(`Flask server error: ${error.message}`);
            if (stderr) console.error(`Flask stderr: ${stderr}`);
            console.log(`Flask stdout: ${stdout}`);
        });
    } catch (error) {
        console.error('Failed to start services:', error);
        app.quit();
    }
});

app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
        if (speechProcess) {
            speechProcess.kill();
        }
        app.quit();
    }
});

app.on('activate', function () {
    if (mainWindow === null) {
        createWindow();
    }
});
