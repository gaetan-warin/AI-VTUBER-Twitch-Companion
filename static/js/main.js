import { initializeModel } from './modules/model.js';
import { initializeSpeech } from './modules/speech.js';
import { initializeMicrophone, checkMicrophoneAccess } from './modules/microphone.js';
import { setupUI } from './modules/ui.js';
import { initializeEffects } from './modules/effects.js';
import { initializeSocket, getInitialConfig } from './modules/socket.js';

async function initializeApp() {
    await initializeSpeech();
    setupUI();
    initializeSocket();
    initializeMicrophone();
    initializeModel();
    initializeEffects();
    getInitialConfig();
    checkMicrophoneAccess();
}

// Example of using Electron's IPC
document.getElementById('startStreamBtn').addEventListener('click', () => {
    window.electron.send('start-stream');
});

document.getElementById('stopStreamBtn').addEventListener('click', () => {
    window.electron.send('stop-stream');
});

// Initial setup
$(document).ready(() => initializeApp());