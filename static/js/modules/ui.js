import { startRecording, stopRecording, isCurrentlyRecording } from './microphone.js';
import { loadAvatarModel, getModelPath } from './model.js';
import { saveConfig, saveModalConfig, config, populateSelectElement } from './config.js';
import { checkListenerStatus, startListener, stopListener, emit } from './socket.js';
import { areVoicesReady } from './speech.js';
import { updateCelebrationSound } from './effects.js';
import { initializeFileManager, openFileManagerModal } from './fileManager.js';
import { startScreenStream, captureLastFrameFromStream, stopScreenStream } from './screenRecorder.js';

// Global variable to store captured screenshot
window.sharedScreenshot = null;

// Global variable to hold the active stream
window.screenStream = null;

export function setupUI() {
    setupEventListeners();
    setupBackgroundImage();
    setupAvatarModel();
    setupTwitchFields();
    setupRecordingButton();
    setupWaveToggle();
    setupWakeWordToggle();
    $('#waveCanvas').hide();
    initializeFileManager();
    setupFileManagerButton();
}

function setupEventListeners() {
    $('#speakBtn').on('click', function () {
        if (!areVoicesReady()) {
            alert("Speech synthesis voices are not loaded yet. Please wait a moment and try again.");
            return;
        }
        const text = $('#makeItSpeak').val().trim();
        if (text) {
            emit('speak', { text, source: 'text' });
            $('#makeItSpeak').val('');
        }
    });

    // Start Stream button event
    $('#startStreamBtn').off('click').on('click', async () => {
        try {
            window.screenStream = await startScreenStream();
            $('#startStreamBtn').hide();
            $('#stopStreamBtn').show();
        } catch (e) {
            console.error("Stream start failed:", e);
        }
    });

    // Stop Stream button event
    $('#stopStreamBtn').off('click').on('click', () => {
        if (window.screenStream) {
            stopScreenStream(window.screenStream);
            window.screenStream = null;
            alert("Stream stopped.");
            $('#stopStreamBtn').hide();
            $('#startStreamBtn').show();
        }
    });

    // Ask AI button event uses the active stream, capturing its last frame
    $('#askAIBtn').off('click').on('click', async function () {
        if (!areVoicesReady()) {
            alert("Speech synthesis voices are not loaded yet. Please wait a moment and try again.");
            return;
        }
        const text = $('#makeItSpeak').val().trim();
        let screenshot = null;
        if (window.screenStream) {
            try {
                screenshot = await captureLastFrameFromStream(window.screenStream);
            } catch (e) {
                console.error("Failed to capture last frame from stream:", e);
            }
        }
        if (text) {
            emit('ask_ai', { text, source: 'text', screenshot });
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
    $('#celebrateSound').on('change', updateCelebrationSound);

    // Add test celebration buttons handlers
    $('#testFollowBtn').on('click', () => {
        emit('trigger_event', {
            event_type: 'follow',
            username: 'TestUser'
        });
    });

    $('#testSubBtn').on('click', () => {
        emit('trigger_event', {
            event_type: 'sub',
            username: 'TestUser'
        });
    });

    $('#fileManager').on('click', openFileManagerModal);

    $('#twitchConnectBtn').off('click').on('click', connectToTwitch);
}

function connectToTwitch() {
    const twitchClientId = $('#twitchClientId').val();
    const redirectUri = 'http://localhost:5000/auth/twitch/callback';
    // Use non-encoded redirectUri if your Twitch dashboard is configured with the decoded URL
    if (!twitchClientId) {
        alert("Twitch Client ID is not configured.");
        return;
    }
    const authUrl = `https://id.twitch.tv/oauth2/authorize?client_id=${twitchClientId}&redirect_uri=${redirectUri}&response_type=token&scope=chat:read+chat:edit`;
    window.open(authUrl, 'TwitchAuth', 'width=600,height=600');
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
    $('#backgroundImage').on('change', function () {
        const selectedImage = $(this).val();
        if (selectedImage === 'greenscreen') {
            $('body').css({
                backgroundImage: 'none',
                backgroundColor: '#00ff00'
            });
        } else {
            $('body').css({
                backgroundImage: `url('/static/images/background/${selectedImage}')`,
                backgroundPosition: 'center',
                backgroundSize: 'cover',
                backgroundColor: ''
            });
        }
    });
}
async function setupAvatarModel() {
    $('#avatarModel').on('change', async function () {
        const selectedModel = $(this).val();
        const modelPath = await getModelPath(selectedModel);
        loadAvatarModel(modelPath);
    });
}

function setupTwitchFields() {
    $('#twitchToken, #twitchClientId').addClass('blurry')
        .on('focus', function () { $(this).removeClass('blurry'); })
        .on('blur', function () { $(this).addClass('blurry'); });
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
    $('#waveToggle').on('change', function () {
        if (isCurrentlyRecording()) {
            $('#waveCanvas').toggle($(this).is(':checked'));
        }
    });
}

function setupWakeWordToggle() {
    const $container = $('#wakeWordContainer');
    const $checkbox = $('#wakeWordEnabled');

    function updateWakeWordVisibility() {
        $container.toggle($checkbox.is(':checked'));
    }

    $checkbox.on('change', updateWakeWordVisibility);
    updateWakeWordVisibility(); // Call this immediately to set initial state
}

function setupFileManagerButton() {
    $('#fileManager').on('click', openFileManagerModal);
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
        const { config: configData, avatarList, backgroundList, ollamaModelList, soundsList } = data.data;

        const populationPromises = [
            populateSelectElement('#avatarModel', avatarList),
            populateSelectElement('#backgroundImage', backgroundList),
            populateSelectElement('#ollamaModel', ollamaModelList),
            populateSelectElement('#celebrateSound', soundsList),
        ];

        Promise.all(populationPromises)
            .then(() => {
                console.log('All fields populated');
                if (!$('#backgroundImage option[value="greenscreen"]').length)
                    $('#backgroundImage').append(new Option('greenscreen', 'greenscreen'));

                // Set configuration before other UI updates
                config.set(configData);

                // Explicitly set wake word checkbox state
                const $wakeWordCheckbox = $('#wakeWordEnabled');
                $wakeWordCheckbox.prop('checked', configData.WAKE_WORD_ENABLED === true);

                // Update wake word container visibility
                $('#wakeWordContainer').toggle($wakeWordCheckbox.is(':checked'));

                // Set fixed language if available
                if (configData.FIXED_LANGUAGE) {
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

export function updateTwitchToken(data) {
    const twitchTokenInput = document.getElementById('twitchToken');
    if (twitchTokenInput)
        twitchTokenInput.value = data.twitchToken;
}
