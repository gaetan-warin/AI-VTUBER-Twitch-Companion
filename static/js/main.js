let modelPath = '';
const synth = window.speechSynthesis;
const mouthState = { value: 0 };
let isSpeaking = false;
let voicesReady = false;
let currentModel = null;

// WebSocket configuration
const socket = io({
    transports: ['websocket'],
    reconnectionAttempts: 5,
    timeout: 3000
});

// Add this audio element to the body
const celebrationAudio = new Audio('static/mp3/success.mp3');
celebrationAudio.volume = 0.3;
celebrationAudio.preload = 'auto';

// Initialize application
function main(modelPath) {
    if (!modelPath) {
        console.error('Model path not set.');
        return;
    }

    const app = new PIXI.Application({
        view: $('#canvas')[0],
        autoStart: true,
        resizeTo: window,
        transparent: true,
        antialias: true
    });

    app.ticker.add(() => {
        if (isSpeaking)
            mouthState.value = Math.sin(performance.now() / 200) / 2 + 0.5;
    });

    loadModel(app, modelPath);
}

async function loadModel(app, modelPath) {
    try {
        const model = await PIXI.live2d.Live2DModel.from(modelPath);
        app.stage.addChild(model);
        currentModel = model;

        // Model positioning
        model.anchor.set(0.5, 0.5);
        model.position.set(innerWidth / 2, innerHeight / 2);
        
        // Model sizing
        const size = Math.min(innerWidth, innerHeight) * 0.8;
        model.width = size;
        model.height = size;

        // Save the original update function

        model.internalModel.motionManager.update = () => {
            if (modelPath.includes("model.json")) {
                model.internalModel.coreModel.setParamFloat('PARAM_MOUTH_OPEN_Y', mouthState.value);
            } else {
               var parameterIndex = currentModel.internalModel.coreModel.getParameterIndex("ParamMouthOpenY");
                currentModel.internalModel.coreModel.setParameterValueByIndex(parameterIndex , mouthState.value);
            }
        }
    } catch (error) {
        console.error('Model loading error:', error);
    }
}

function loadAvatarModel(modelPath) {
    if (!modelPath) {
        console.error('Model path not set.');
        return;
    }

    if (currentModel) {
        currentModel.destroy();
        currentModel = null;
    }

    main(modelPath);
}

// Voice initialization
synth.onvoiceschanged = () => {
    voicesReady = true;
    console.log('Voices loaded:', synth.getVoices());
};

function showSpeechBubble(text) {
    const bubble = $('#speech-bubble');
    bubble.text(text).show();

    if (currentModel) {
        const bounds = currentModel.getBounds();
        const x = window.innerWidth / 2;
        const y = (window.innerHeight / 2) - bounds.height / 2 - 50;

        bubble.css({
            left: `${x - bubble.outerWidth() / 2}px`,
            top: `${y}px`
        });
    }
}

function hideSpeechBubble() {
    $('#speech-bubble').hide();
}

function speak(text) {
    if (!text || !voicesReady) {
        console.log("Voices not loaded yet.");
        return;
    }

    if (isSpeaking) {
        synth.cancel();
        isSpeaking = false;
        gsap.killTweensOf(mouthState);
        hideSpeechBubble();
    }

    // Split text into sentences and wait times
    const parts = text.split(/(\{\*\d+\*\})|([.!?]\s+)/).filter(Boolean);

    let partIndex = 0;

    // Function to speak each part
    function speakNextPart() {
        if (partIndex < parts.length) {
            let currentPart = parts[partIndex];
            const waitMatch = currentPart.match(/\{\*(\d+)\*\}/);

            if (waitMatch) {
                const waitTime = parseInt(waitMatch[1], 10);
                setTimeout(() => {
                    partIndex++;
                    speakNextPart();
                }, waitTime);
            } else {
                // Extract punctuation from the part to be spoken
                const punctuationMatch = currentPart.match(/[.!?]\s*$/);
                const punctuation = punctuationMatch ? punctuationMatch[0] : '';
                const textToSpeak = currentPart.replace(/[.!?]\s*$/, '').trim();
                showSpeechBubble(textToSpeak + punctuation); // Show speech bubble with punctuation

                const utterance = new SpeechSynthesisUtterance(textToSpeak);
                const voice = synth.getVoices().find(v => v.name.includes('Female')) || synth.getVoices()[0];

                Object.assign(utterance, {
                    voice: voice,
                    pitch: 1.1,
                    rate: 0.95
                });

                utterance.onstart = () => {
                    isSpeaking = true;
                    // Animate mouth using GSAP with sine wave pattern
                    gsap.to(mouthState, {
                        duration: 0.2,
                        value: 1,
                        repeat: -1,
                        yoyo: true,
                        ease: "sine.inOut",
                        modifiers: {
                            value: () => Math.abs(Math.sin(performance.now() / 200)) * 0.8
                        }
                    });
                };

                utterance.onend = () => {
                    isSpeaking = false;
                    gsap.killTweensOf(mouthState);
                    gsap.to(mouthState, {
                        duration: 0.3,
                        value: 0,
                        ease: "power2.out"
                    });
                    hideSpeechBubble(); // Hide speech bubble when speech ends
                    partIndex++;
                    // Add a short pause for punctuation
                    if (punctuation) {
                        setTimeout(speakNextPart, 500);
                    } else {
                        speakNextPart();
                    }
                };

                synth.speak(utterance);
            }
        }
    }

    speakNextPart(); // Start speaking the first part
}

function askAI(text) {
    if (!text) {
        console.log("No text provided.");
        return;
    }

    socket.emit('ask_ai', { text });
}

function setupEventListeners() {
    $('#speakBtn, #askAIBtn').on('click', function() {
        const text = $('#makeItSpeak').val().trim();
        if (text) {
            socket.emit(this.id === 'speakBtn' ? 'speak' : 'ask_ai', { text });
            $('#makeItSpeak').val('');
        }
    });

    $('#makeItSpeak').on('keydown', (event) => {
        if (event.ctrlKey && event.key === 'Enter') {
            const text = $(event.target).val().trim();
            if (text) {
                socket.emit('speak', { text });
                $(event.target).val('');
            }
        }
    });

    $('#toggleSidebarBtn').on('click', () => {
        const sidebar = $('#sidebar');
        sidebar.toggleClass('collapsed');
        $('#toggleSidebarBtn').text(sidebar.hasClass('collapsed') ? 'Expand' : 'Collapse');
        $('#toggleSidebarBtnCollapsed').toggle(sidebar.hasClass('collapsed'));
    });

    $('#toggleSidebarBtnCollapsed').on('click', () => {
        $('#sidebar').removeClass('collapsed');
        $('#toggleSidebarBtn').text('Collapse');
        $('#toggleSidebarBtnCollapsed').hide();
    });

    $('.tab-button').on('click', function() {
        $('.tab-button').removeClass('active');
        $('.tab-content').hide();
        $(this).addClass('active');
        $('#' + $(this).data('tab')).show();
    });

    $('#saveConfigBtn').on('click', saveConfig);

    const avatarModelSelect = $('#avatarModel');
    const backgroundImageSelect = $('#backgroundImage');

    backgroundImageSelect.on('change', function() {
        const selectedImage = $(this).val();
        $('body').css({
            backgroundImage: `url('/static/images/background/${selectedImage}')`,
            backgroundPosition: 'center',
            backgroundSize: 'cover'
        });
    });

    avatarModelSelect.on('change', function() {
        const selectedModel = $(this).val();
        const modelPath = selectedModel === 'mao_pro' ? `models/${selectedModel}/mao_pro.model3.json` :
                          selectedModel === 'haru' ? `models/${selectedModel}/haru_greeter_t03.model3.json` :
                          `models/${selectedModel}/${selectedModel}.model.json`;
        loadAvatarModel(modelPath);
    });

    $('#TWITCH_TOKEN, #clientId').addClass('blurry').on('focus', function() {
        $(this).removeClass('blurry');
    }).on('blur', function() {
        $(this).addClass('blurry');
    });

    $('#configBtn').on('click', () => {
        $('#configModal').show();
    });

    $('.close').on('click', () => {
        $('#configModal').hide();
    });

    $(window).on('click', (event) => {
        if (event.target === $('#configModal')[0]) {
            $('#configModal').hide();
        }
    });

    $('#saveModalConfigBtn').on('click', saveModalConfig);
}

function initializeApp() {
    socket.emit('get_init_cfg');
}

socket.on('init_cfg', function(data) {
    console.log("Received initial configuration:", data);  // Debugging line
    if (data.status === 'success') {
        const { config, avatarList, backgroundList, ollamaModelList } = data.data;

        // Populate select elements
        populateSelectElement('#avatarModel', avatarList);
        populateSelectElement('#backgroundImage', backgroundList);
        populateSelectElement('#ollamaModel', ollamaModelList);

        // Apply configuration
        applyConfig(config);

        checkListenerStatus();
    } else {
        console.error('Failed to load initial configuration:', data.message);
    }
});

function populateSelectElement(selector, items) {
    const selectElement = $(selector);
    selectElement.empty();
    items.forEach(item => {
        selectElement.append(new Option(item, item));
    });
}

function saveConfig() {
    const config = getConfigValues([
        'personaName', 'personaRole', 'prePrompt', 'avatarModel', 'backgroundImage',
        'channelName', 'twitchToken', 'clientId', 'extraDelayListener',
        'nbSpamMessage', 'ollamaModel', 'botNameFollowSub', 'keyWordFollow',
        'keyWordSub', 'delimiterName', 'delimiterNameEnd'
    ]);
    console.log("save config:", config);
    socket.emit('save_config', config);
}

function saveModalConfig() {
    $('#configModal').hide();
}

function camelToSnakeCase(str) {
    return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
}

function snakeToCamelCase(str) {
    return str.toLowerCase().replace(/([-_][a-z])/g, group =>
        group
          .toUpperCase()
          .replace('-', '')
          .replace('_', '')
      );;
}

function getConfigValues(fields) {
    const config = {};
    fields.forEach(field => {
        const snakeField = camelToSnakeCase(field);
        config[snakeField.toUpperCase()] = $(`#${field}`).val().trim();
    });
    return config;
}

function showQuestionDisplay(text) {
    const questionDisplay = $('#question-display');
    questionDisplay.text(text).show();
    clearTimeout(questionDisplay.data('hideTimeout'));
    questionDisplay.data('hideTimeout', setTimeout(() => {
        questionDisplay.hide();
    }, 10000));
}

function triggerFireworks() {
    // Play celebration sound
    celebrationAudio.currentTime = 0; // Reset audio to start
    const playPromise = celebrationAudio.play();

    if (playPromise !== undefined) {
        playPromise.catch(error => {
            console.log("Audio playback failed:", error);
        });
    }

    // Create multiple bursts of confetti
    const duration = 5 * 1000;
    const animationEnd = Date.now() + duration;
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };

    function randomInRange(min, max) {
        return Math.random() * (max - min) + min;
    }

    const interval = setInterval(function() {
        const timeLeft = animationEnd - Date.now();

        if (timeLeft <= 0) {
            return clearInterval(interval);
        }

        const particleCount = 50 * (timeLeft / duration);

        // Create confetti from random positions
        confetti({
            ...defaults,
            particleCount,
            origin: { x: randomInRange(0.1, 0.3), y: Math.random() - 0.2 }
        });
        confetti({
            ...defaults,
            particleCount,
            origin: { x: randomInRange(0.7, 0.9), y: Math.random() - 0.2 }
        });
    }, 250);

    // Add some special effects
    confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#ff0000', '#00ff00', '#0000ff']
    });
}

function showNotification(type, message) {
    const notification = $('#notification');
    notification.text(message).attr('class', `notification ${type}`).addClass('show');
    setTimeout(() => {
        notification.removeClass('show');
    }, 3000);
}

// Socket event listeners
socket.on('speak_text', data => speak(data.text));
socket.on('ai_response', data => speak(data.text));
socket.on('display_question', showQuestionDisplay);
socket.on('fireworks', triggerFireworks);
socket.on('connect', () => console.log('WebSocket connected:', socket.id));
socket.on('disconnect', () => console.log('WebSocket disconnected'));

socket.on('model_path', data => {
    modelPath = data.path;
    console.log("Received model path:", modelPath);
    main(modelPath);
});

socket.on('save_config_response', function(response) {
    if (response.status === 'success') {
        showNotification('success', 'Configuration saved successfully');
    } else {
        showNotification('error', response.message);
    }
});

function applyConfig(config) {
    const fields = [
        'AVATAR_MODEL', 'PERSONA_NAME', 'PERSONA_ROLE', 'PRE_PROMPT', 'BACKGROUND_IMAGE',
        'CHANNEL_NAME', 'TWITCH_TOKEN', 'CLIENT_ID', 'EXTRA_DELAY_LISTENER', 'NB_SPAM_MESSAGE',
        'OLLAMA_MODEL', 'BOT_NAME_FOLLOW_SUB', 'KEY_WORD_FOLLOW', 'KEY_WORD_SUB',
        'DELIMITER_NAME', 'DELIMITER_NAME_END'
    ];

    fields.forEach(field => {
        const $field = $(`#${snakeToCamelCase(field)}`);
        if ($field.is('select')) {
            $field.find(`option[value="${config[field]}"]`).prop('selected', true);
            $field.trigger('change');
        } else {
            $field.val(config[field]);
        }
    });

    if (config.BACKGROUND_IMAGE) {
        $('body').css({
            backgroundImage: `url('/static/images/background/${config.BACKGROUND_IMAGE}')`,
            backgroundPosition: 'center',
            backgroundSize: 'cover'
        });
    }

    if (config.AVATAR_MODEL) {
        const modelPath = config.AVATAR_MODEL === 'mao_pro' ? `models/${config.AVATAR_MODEL}/mao_pro.model3.json` :
                          config.AVATAR_MODEL === 'haru' ? `models/${config.AVATAR_MODEL}/haru_greeter_t03.model3.json` :
                          `models/${config.AVATAR_MODEL}/${config.AVATAR_MODEL}.model.json`;
        loadAvatarModel(modelPath);
    }
}

function updateListenerStatus(status) {
    const statusText = $('#listenerStatusText');
    statusText.text(status ? 'Running' : 'Stopped');
    statusText.css('color', status ? 'green' : 'red');
}

function checkListenerStatus() {
    socket.emit('get_listener_status');
}

$('#startListenerBtn').on('click', () => {
    socket.emit('start_listener');
});

$('#stopListenerBtn').on('click', () => {
    socket.emit('stop_listener');
});

socket.on('listener_update', (data) => {
    if (data.status === 'success') {
        updateListenerStatus(data.action === 'start');
    } else {
        alert(`Failed to ${data.action} listener: ${data.message}`);
    }
});

// Initial setup
$(document).ready(() => {
    setupEventListeners();
    socket.connect();
    initializeApp();
});