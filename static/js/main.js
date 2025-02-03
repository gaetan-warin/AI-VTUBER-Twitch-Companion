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

// Configuration object
const config = {
    fields: [
        'AVATAR_MODEL', 'PERSONA_NAME', 'PERSONA_ROLE', 'PRE_PROMPT', 'BACKGROUND_IMAGE',
        'CHANNEL_NAME', 'TWITCH_TOKEN', 'CLIENT_ID', 'EXTRA_DELAY_LISTENER', 'NB_SPAM_MESSAGE',
        'OLLAMA_MODEL', 'BOT_NAME_FOLLOW_SUB', 'KEY_WORD_FOLLOW', 'KEY_WORD_SUB',
        'DELIMITER_NAME', 'DELIMITER_NAME_END', 'PREFERRED_MICROPHONE'
    ],
    get: function() {
        return this.fields.reduce((acc, field) => {
            acc[field] = $(`#${this.snakeToCamelCase(field)}`).val().trim();
            return acc;
        }, {});
    },
    set: function(data) {
        this.fields.forEach(field => {
            const $field = $(`#${this.snakeToCamelCase(field)}`);
            if ($field.length && data[field]) {
                if ($field.is('select')) {
                    $field.val(data[field]).trigger('change');
                } else {
                    $field.val(data[field]);
                }
            }
        });
    },
    snakeToCamelCase: function(str) {
        return str.toLowerCase().replace(/([-_][a-z])/g, group =>
            group.toUpperCase().replace('-', '').replace('_', '')
        );
    },
    camelToSnakeCase: function(str) {
        return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
    }
};

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

    const parts = text.split(/(\{\*\d+\*\})|([.!?]\s+)/).filter(Boolean);
    let partIndex = 0;

    function speakNextPart() {
        if (partIndex < parts.length) {
            const currentPart = parts[partIndex];
            const waitMatch = currentPart.match(/\{\*(\d+)\*\}/);

            if (waitMatch) {
                setTimeout(() => {
                    partIndex++;
                    speakNextPart();
                }, parseInt(waitMatch[1], 10));
            } else {
                const punctuationMatch = currentPart.match(/[.!?]\s*$/);
                const punctuation = punctuationMatch ? punctuationMatch[0] : '';
                const textToSpeak = currentPart.replace(/[.!?]\s*$/, '').trim();
                showSpeechBubble(textToSpeak + punctuation);

                const utterance = new SpeechSynthesisUtterance(textToSpeak);
                const voice = synth.getVoices().find(v => v.name.includes('Female')) || synth.getVoices()[0];

                Object.assign(utterance, {
                    voice: voice,
                    pitch: 1.1,
                    rate: 0.95,
                    onstart: () => {
                        isSpeaking = true;
                        animateMouth();
                    },
                    onend: () => {
                        isSpeaking = false;
                        stopMouthAnimation();
                        hideSpeechBubble();
                        partIndex++;
                        setTimeout(speakNextPart, punctuation ? 500 : 0);
                    }
                });

                synth.speak(utterance);
            }
        }
    }

    speakNextPart();
}

function animateMouth() {
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
}

function stopMouthAnimation() {
    gsap.killTweensOf(mouthState);
    gsap.to(mouthState, {
        duration: 0.3,
        value: 0,
        ease: "power2.out"
    });
}

function askAI(text) {
    if (!text) {
        console.log("No text provided.");
        return;
    }

    socket.emit('ask_ai', { text });
}

// Speech Recognition Setup
let recognition = null;
let isRecording = false;

// Update the speech recognition initialization
function initializeSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window)) {
        alert('Speech recognition is not supported in this browser.');
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        if (isSpeaking) {
            synth.cancel();
            isSpeaking = false;
            gsap.killTweensOf(mouthState);
            hideSpeechBubble();
        }
    };

    recognition.onresult = (event) => {
        const text = event.results[event.results.length - 1][0].transcript;
        askAI(text);
    };

    recognition.onend = () => {
        if (isRecording) {
            recognition.start();
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        stopRecording();
    };
}

let audioContext, audioInput, analyser;
const waveCanvas = document.getElementById('waveCanvas');
const microphoneAudio = document.getElementById('microphoneAudio');

function initializeWaveVisualization() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
        console.error('Your browser does not support mediastream');
        return;
    }

    navigator.mediaDevices.getUserMedia({ audio: true, video: false })
        .then(function onSuccess(stream) {
            audioContext = new (window.AudioContext || window.webkitAudioContext || window.mozAudioContext || window.msAudioContext)();
            audioInput = audioContext.createMediaStreamSource(stream);
            analyser = audioContext.createAnalyser();
            audioInput.connect(analyser);

            const binaryData = [stream];
            microphoneAudio.src = window.URL.createObjectURL(new Blob(binaryData, { type: 'application/zip' }));
            microphoneAudio.onloadedmetadata = function(e) { };

            drawSpectrum(analyser);
        })
        .catch(function(e) {
            console.error('Error accessing microphone:', e);
        });
}

function drawSpectrum(analyser) {
    const ctx = waveCanvas.getContext('2d');
    const cwidth = waveCanvas.width;
    const cheight = waveCanvas.height;
    const meterWidth = 8;
    const gap = 2;
    const meterNum = cwidth / (meterWidth + gap);

    const gradient = ctx.createLinearGradient(0, cheight, 0, 0);
    gradient.addColorStop(1, '#a467af');
    gradient.addColorStop(0.3, '#ff0');
    gradient.addColorStop(0, '#f00');
    ctx.fillStyle = gradient;

    function drawMeter() {
        const array = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(array);

        const step = Math.round(array.length / meterNum);
        ctx.clearRect(0, 0, cwidth, cheight);
        for (let i = 0; i < meterNum; i++) {
            const value = array[i * step];
            ctx.fillRect(i * (meterWidth + gap), cheight, meterWidth, -value);
        }
        requestAnimationFrame(drawMeter);
    }

    requestAnimationFrame(drawMeter);
}

function startRecording() {
    if (!recognition) initializeSpeechRecognition();
    if (isSpeaking) {
        synth.cancel();
        isSpeaking = false;
        gsap.killTweensOf(mouthState);
        hideSpeechBubble();
    }

    initializeWaveVisualization();

    recognition.start();
    isRecording = true;
    $('#startRecordingBtn').text('Stop Recording').addClass('recording');
    
    if ($('#waveToggle').is(':checked')) {
        $('#waveCanvas').show();
    }
    
    // Update microphone selection when starting recording
    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(() => updateMicrophoneList())
        .catch(err => {
            console.error('Microphone access denied:', err);
            stopRecording();
        });
}

function stopRecording() {
    if (recognition) {
        recognition.stop();
        isRecording = false;
        $('#startRecordingBtn').text('Start Recording').removeClass('recording');
        $('#waveCanvas').hide();

        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }
    }
}

function updateMicrophoneList() {
    const micSelect = $('#preferredMicrophone');
    micSelect.empty();

    return navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            devices.forEach(device => {
                if (device.kind === 'audioinput') {
                    micSelect.append(new Option(device.label || `Microphone ${micSelect.children().length + 1}`, device.deviceId));
                }
            });
        })
        .catch(err => {
            console.error('Error accessing media devices:', err);
            throw err;
        });
}

function setupEventListeners() {
    $('#speakBtn, #askAIBtn').on('click', function() {
        const text = $('#makeItSpeak').val().trim();
        if (text) {
            socket.emit(this.id === 'speakBtn' ? 'speak' : 'ask_ai', { text });
            $('#makeItSpeak').val('');
        }
    });

    $('#makeItSpeak').on('keydown', event => {
        if (event.ctrlKey && event.key === 'Enter') {
            const text = event.target.value.trim();
            if (text) {
                socket.emit('speak', { text });
                event.target.value = '';
            }
        }
    });

    $('#toggleSidebarBtn, #toggleSidebarBtnCollapsed').on('click', () => {
        const sidebar = $('#sidebar');
        sidebar.toggleClass('collapsed');
        $('#toggleSidebarBtn').text(sidebar.hasClass('collapsed') ? 'Expand' : 'Collapse');
        $('#toggleSidebarBtnCollapsed').toggle(sidebar.hasClass('collapsed'));
    });

    $('.tab-button').on('click', function() {
        $('.tab-button').removeClass('active');
        $('.tab-content').hide();
        $(this).addClass('active');
        $(`#${$(this).data('tab')}`).show();
    });

    $('#saveConfigBtn').on('click', saveConfig);
    $('#configBtn').on('click', () => $('#configModal').show());
    $('.close').on('click', () => $('#configModal').hide());
    $(window).on('click', event => {
        if (event.target === $('#configModal')[0]) $('#configModal').hide();
    });
    $('#saveModalConfigBtn').on('click', saveModalConfig);

    $('#backgroundImage').on('change', function() {
        const selectedImage = $(this).val();
        $('body').css({
            backgroundImage: `url('/static/images/background/${selectedImage}')`,
            backgroundPosition: 'center',
            backgroundSize: 'cover'
        });
    });

    $('#avatarModel').on('change', function() {
        const selectedModel = $(this).val();
        const modelPath = selectedModel === 'mao_pro' ? `models/${selectedModel}/mao_pro.model3.json` :
                          selectedModel === 'haru' ? `models/${selectedModel}/haru_greeter_t03.model3.json` :
                          `models/${selectedModel}/${selectedModel}.model.json`;
        loadAvatarModel(modelPath);
    });

    $('#TWITCH_TOKEN, #clientId').addClass('blurry')
        .on('focus', function() { $(this).removeClass('blurry'); })
        .on('blur', function() { $(this).addClass('blurry'); });

    $('#startRecordingBtn').on('click', () => {
        if (!isRecording) {
            startRecording();
        } else {
            stopRecording();
        }
    });

    $('#preferredMicrophone').on('change', function() {
        if (isRecording) {
            stopRecording();
            startRecording();
        }
    });

    $('#waveToggle').on('change', function() {
        if (isRecording) {
            if ($(this).is(':checked')) {
                $('#waveCanvas').show();
            } else {
                $('#waveCanvas').hide();
            }
        }
    });
}

function initializeApp() {
    socket.emit('get_init_cfg');
}

socket.on('init_cfg', function(data) {
    console.log("Received initial configuration:", data);
    if (data.status === 'success') {
        const { config: configData, avatarList, backgroundList, ollamaModelList } = data.data;

        // Populate select elements and track completion
        const populationPromises = [
            new Promise(resolve => {
                populateSelectElement('#avatarModel', avatarList);
                resolve('avatarModel');
            }),
            new Promise(resolve => {
                populateSelectElement('#backgroundImage', backgroundList);
                resolve('backgroundImage');
            }),
            new Promise(resolve => {
                populateSelectElement('#ollamaModel', ollamaModelList);
                resolve('ollamaModel');
            }),
            new Promise(resolve => {
                updateMicrophoneList().then(() => resolve('microphone'));
            })
        ];

        // Wait for all fields to be populated
        Promise.all(populationPromises)
            .then(results => {
                console.log('All fields populated:', results);
                // Apply configuration after all fields are ready
                config.set(configData);
                checkListenerStatus();
            })
            .catch(error => {
                console.error('Error during field population:', error);
            });
    } else {
        console.error('Failed to load initial configuration:', data.message);
    }
});

function populateSelectElement(selector, items) {
    const selectElement = $(selector);
    if (!selectElement.length) {
        console.error(`Select element ${selector} not found`);
        return false;
    }
    selectElement.empty();
    if (Array.isArray(items)) {
        items.forEach(item => {
            selectElement.append(new Option(item, item));
        });
        return true;
    }
    console.error(`Invalid items array for ${selector}`);
    return false;
}

function saveConfig() {
    const configData = config.get();
    console.log("save config:", configData);
    socket.emit('save_config', configData);
}

function saveModalConfig() {
    $('#configModal').hide();
    saveConfig();
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
    celebrationAudio.currentTime = 0;
    celebrationAudio.play().catch(error => console.log("Audio playback failed:", error));

    const duration = 5 * 1000;
    const animationEnd = Date.now() + duration;
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };

    const interval = setInterval(() => {
        const timeLeft = animationEnd - Date.now();
        if (timeLeft <= 0) return clearInterval(interval);
        const particleCount = 50 * (timeLeft / duration);
        confetti({ ...defaults, particleCount, origin: { x: Math.random(), y: Math.random() - 0.2 } });
    }, 250);

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
    setTimeout(() => notification.removeClass('show'), 3000);
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
    showNotification(response.status === 'success' ? 'success' : 'error', 
                     response.status === 'success' ? 'Configuration saved successfully' : response.message);
});
socket.on('listener_update', (data) => {
    if (data.status === 'success') {
        updateListenerStatus(data.action === 'start');
    } else {
        alert(`Failed to ${data.action} listener: ${data.message}`);
    }
});

function updateListenerStatus(status) {
    const statusText = $('#listenerStatusText');
    statusText.text(status ? 'Running' : 'Stopped').css('color', status ? 'green' : 'red');
}

function checkListenerStatus() {
    socket.emit('get_listener_status');
}

$('#startListenerBtn').on('click', () => socket.emit('start_listener'));
$('#stopListenerBtn').on('click', () => socket.emit('stop_listener'));

// Initial setup
$(document).ready(() => {
    setupEventListeners();
    socket.connect();
    initializeApp();
    $('#waveCanvas').hide();
});