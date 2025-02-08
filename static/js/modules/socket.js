import { speak } from './speech.js';
import { showQuestionDisplay, handleInitialConfig, handleSaveConfigResponse, handleListenerUpdate, updateTwitchToken } from './ui.js';
import { triggerFireworks } from './effects.js';
import { loadAvatarModel } from './model.js';
import { handleDocumentsList, handleDocumentDeleted, handleDocumentUploaded } from './fileManager.js';

// Export the socket instance
export const socket = io({
    transports: ['websocket'],
    reconnectionAttempts: 5,
    timeout: 3000
});

export function initializeSocket() {
    socket.on('connect', () => console.log('WebSocket connected:', socket.id));
    socket.on('disconnect', () => console.log('WebSocket disconnected'));

    socket.on('init_cfg', handleInitialConfig);
    socket.on('speak_text', data => {
        speak(data.text, data.fixedLanguage);
    });
    socket.on('ai_response', data => {
        speak(data.text, data.fixedLanguage);
    });
    socket.on('display_question', showQuestionDisplay);
    socket.on('fireworks', triggerFireworks);
    socket.on('model_path', data => loadAvatarModel(data.path));
    socket.on('save_config_response', handleSaveConfigResponse);
    socket.on('listener_update', handleListenerUpdate);
    socket.on('documents_list', handleDocumentsList);
    socket.on('document_deleted', handleDocumentDeleted);
    socket.on('document_uploaded', handleDocumentUploaded);
    socket.on('update_twitch_token', (data) => updateTwitchToken(data));
}

export function askAI(text) {
    if (!text) {
        console.log("No text provided.");
        return;
    }
    socket.emit('ask_ai', { text });
}

export function speakText(text, fixedLanguage = null) {
    socket.emit('speak', { text, fixedLanguage });
}

export function getInitialConfig() {
    socket.emit('get_init_cfg');
}

export function checkListenerStatus() {
    socket.emit('get_listener_status');
}

export function startListener() {
    socket.emit('start_listener');
}

export function stopListener() {
    socket.emit('stop_listener');
}

export function saveConfig(configData) {
    socket.emit('save_config', configData);
}

export function emit(canal, data) {
    if (canal === 'speak' || canal === 'ask_ai') {
        const payload = {
            ...data,
            source: data.fromMicrophone ? 'microphone' : 'text'
        };
        socket.emit(canal, payload);
    } else {
        socket.emit(canal, data);
    }
}