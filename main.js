const { app, BrowserWindow } = require('electron');
const { exec } = require('child_process');
const path = require('path');
const fs = require('fs');

let mainWindow;
let speechProcess;

function checkSpeechServer() {
    return new Promise((resolve) => {
        const checkInterval = setInterval(() => {
            try {
                const status = JSON.parse(fs.readFileSync('speech-server-status.json'));
                if (status.status === 'running') {
                    clearInterval(checkInterval);
                    resolve(true);
                }
            } catch (e) {
                // File doesn't exist yet or can't be read
            }
        }, 1000);

        // Timeout after 30 seconds
        setTimeout(() => {
            clearInterval(checkInterval);
            resolve(false);
        }, 30000);
    });
}

async function startSpeechServer() {
    return new Promise((resolve, reject) => {
        speechProcess = exec('node speechServer.js', async (error, stdout, stderr) => {
            if (error) {
                console.error(`Speech server error: ${error.message}`);
                reject(error);
                return;
            }
            if (stderr) console.error(`Speech stderr: ${stderr}`);
            console.log(`Speech stdout: ${stdout}`);
        });

        checkSpeechServer().then(isRunning => {
            if (isRunning) {
                console.log('Speech server started successfully');
                resolve(true);
            } else {
                console.error('Speech server failed to start');
                reject(new Error('Speech server timeout'));
            }
        });
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
            nodeIntegration: false
        }
    });

    mainWindow.loadURL('http://localhost:5000');

    mainWindow.on('closed', function () {
        mainWindow = null;
    });
}

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
