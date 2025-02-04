import { startRecording, stopRecording, isCurrentlyRecording } from './microphone.js';
import { loadAvatarModel, getModelPath } from './model.js';
import { saveConfig, saveModalConfig, config, populateSelectElement } from './config.js';
import { checkListenerStatus, startListener, stopListener, emit } from './socket.js';
import { areVoicesReady } from './speech.js';

export function setupUI() {
    setupEventListeners();
    setupBackgroundImage();
    setupAvatarModel();
    setupTwitchFields();
    setupRecordingButton();
    setupWaveToggle();
    $('#waveCanvas').hide();
    setupLanguageControls();
}

function setupEventListeners() {
    $('#speakBtn, #askAIBtn').on('click', function() {
        if (!areVoicesReady()) {
            alert("Speech synthesis voices are not loaded yet. Please wait a moment and try again.");
            return;
        }
        const text = $('#makeItSpeak').val().trim();
        if (text) {
            emit(this.id === 'speakBtn' ? 'speak' : 'ask_ai', { 
                text,
                source: 'text'
            });
            $('#makeItSpeak').val('');
        }
    });

    $('#makeItSpeak').on('keydown', event => {
        if (event.ctrlKey && event.key === 'Enter') {
            if (!areVoicesReady()) {
                alert("Speech synthesis voices are not loaded yet. Please wait a moment and try again.");
                return;
            }
            const text = event.target.value.trim();
            if (text) {
                emit('speak', { 
                    text,
                    fixedLanguage: $('#fixedLanguage').val()
                });
                event.target.value = '';
            }
        }
    });

    $('#toggleSidebarBtn, #toggleSidebarBtnCollapsed').on('click', toggleSidebar);
    $('.tab-button').on('click', switchTab);
    $('#saveConfigBtn').on('click', () => saveConfig());
    $('#configBtn').on('click', () => $('#configModal').show());
    $('.close').on('click', () => $('#configModal').hide());
    $(window).on('click', event => {
        if (event.target === $('#configModal')[0]) $('#configModal').hide();
    });
    $('#saveModalConfigBtn').on('click', saveModalConfig);

    $('#startListenerBtn').on('click', startListener);
    $('#stopListenerBtn').on('click', stopListener);
}

function toggleSidebar() {
    const sidebar = $('#sidebar');
    sidebar.toggleClass('collapsed');
    $('#toggleSidebarBtn').text(sidebar.hasClass('collapsed') ? 'Expand' : 'Collapse');
    $('#toggleSidebarBtnCollapsed').toggle(sidebar.hasClass('collapsed'));
}

function switchTab() {
    $('.tab-button').removeClass('active');
    $('.tab-content').hide();
    $(this).addClass('active');
    $(`#${$(this).data('tab')}`).show();
}

function setupBackgroundImage() {
    $('#backgroundImage').on('change', function() {
        const selectedImage = $(this).val();
        $('body').css({
            backgroundImage: `url('/static/images/background/${selectedImage}')`,
            backgroundPosition: 'center',
            backgroundSize: 'cover'
        });
    });
}

function setupAvatarModel() {
    $('#avatarModel').on('change', function() {
        const selectedModel = $(this).val();
        const modelPath = getModelPath(selectedModel);
        loadAvatarModel(modelPath);
    });
}

function setupTwitchFields() {
    $('#TWITCH_TOKEN, #clientId').addClass('blurry')
        .on('focus', function() { $(this).removeClass('blurry'); })
        .on('blur', function() { $(this).addClass('blurry'); });
}

function setupRecordingButton() {
    $('#startRecordingBtn').on('click', () => {
        if (!isCurrentlyRecording()) {
            startRecording();
        } else {
            stopRecording();
        }
    });
}

function setupWaveToggle() {
    $('#waveToggle').on('change', function() {
        if (isCurrentlyRecording()) {
            $('#waveCanvas').toggle($(this).is(':checked'));
        }
    });
}

function setupLanguageControls() {
    $('#fixedLanguage').on('change', function() {
        saveConfig();
    });
}

export function showNotification(type, message) {
    const notification = $('#notification');
    notification.text(message).attr('class', `notification ${type}`).addClass('show');
    setTimeout(() => notification.removeClass('show'), 3000);
}

export function showQuestionDisplay(text) {
    const questionDisplay = $('#question-display');
    questionDisplay.text(text).show();
    clearTimeout(questionDisplay.data('hideTimeout'));
    questionDisplay.data('hideTimeout', setTimeout(() => {
        questionDisplay.hide();
    }, 10000));
}

export function updateListenerStatus(status) {
    const statusText = $('#listenerStatusText');
    statusText.text(status ? 'Running' : 'Stopped').css('color', status ? 'green' : 'red');
}

export function handleInitialConfig(data) {
    console.log("Received initial configuration:", data);
    if (data.status === 'success') {
        const { config: configData, avatarList, backgroundList, ollamaModelList } = data.data;

        const populationPromises = [
            populateSelectElement('#avatarModel', avatarList),
            populateSelectElement('#backgroundImage', backgroundList),
            populateSelectElement('#ollamaModel', ollamaModelList),
        ];

        Promise.all(populationPromises)
            .then(() => {
                console.log('All fields populated');
                config.set(configData);
                
                // Set fixed language if available
                if (configData.fixedLanguage) {
                    $('#fixedLanguage').val(configData.FIXED_LANGUAGE);
                }
                
                checkListenerStatus();
            })
            .catch(error => {
                console.error('Error during field population:', error);
            });
    } else {
        console.error('Failed to load initial configuration:', data.message);
    }
}

export function handleSaveConfigResponse(response) {
    showNotification(
        response.status === 'success' ? 'success' : 'error',
        response.status === 'success' ? 'Configuration saved successfully' : response.message
    );
}

export function handleListenerUpdate(data) {
    if (data.status === 'success') {
        updateListenerStatus(data.action === 'start');
    } else {
        alert(`Failed to ${data.action} listener: ${data.message}`);
    }
}
