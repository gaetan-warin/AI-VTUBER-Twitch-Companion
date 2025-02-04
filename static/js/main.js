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
}

// Initial setup
$(document).ready(() => {
    initializeApp();
    $('#waveCanvas').hide();
    checkMicrophoneAccess();
});