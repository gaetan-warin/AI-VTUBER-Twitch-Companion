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
celebrationAudio.volume = 0.3; // Set volume to 30%
celebrationAudio.preload = 'auto'; // Preload the audio

// Initialize application
function main(modelPath) {
    if (!modelPath) {
        console.error('Model path not set.');
        return;
    }

    const app = new PIXI.Application({
        view: document.getElementById('canvas'),
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
    const bubble = document.getElementById('speech-bubble');
    bubble.textContent = text;
    bubble.style.display = 'block';

    if (currentModel) {
        const bounds = currentModel.getBounds();
        const x = window.innerWidth / 2;
        const y = (window.innerHeight / 2) - bounds.height / 2 - 50;

        bubble.style.left = `${x - bubble.offsetWidth / 2}px`;
        bubble.style.top = `${y}px`;
    }
}

function hideSpeechBubble() {
    const bubble = document.getElementById('speech-bubble');
    bubble.style.display = 'none';
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
    const speakBtn = document.getElementById('speakBtn');
    if (speakBtn) {
        speakBtn.addEventListener('click', () => {
            const inputField = document.getElementById('makeItSpeak');
            const text = inputField ? inputField.value.trim() : '';
            if (text) {
                socket.emit('speak', { text });
                inputField.value = ''; // Clear the input field
            }
        });
    }

    const askAIBtn = document.getElementById('askAIBtn');
    if (askAIBtn) {
        askAIBtn.addEventListener('click', () => {
            const inputField = document.getElementById('makeItSpeak');
            const text = inputField ? inputField.value.trim() : '';
            if (text) {
                askAI(text);
                inputField.value = ''; // Clear the input field
            }
        });
    }

    const makeItSpeak = document.getElementById('makeItSpeak');
    if (makeItSpeak) {
        makeItSpeak.addEventListener('keydown', (event) => {
            if (event.ctrlKey && event.key === 'Enter') {
                const inputField = event.target;
                const text = inputField ? inputField.value.trim() : '';
                if (text) {
                    socket.emit('speak', { text });
                    inputField.value = ''; // Clear the input field
                }
            }
        });
    }

    const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
    if (toggleSidebarBtn) {
        toggleSidebarBtn.addEventListener('click', () => {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.toggle('collapsed');
            toggleSidebarBtn.textContent = sidebar.classList.contains('collapsed') ? 'Expand' : 'Collapse';
            const toggleSidebarBtnCollapsed = document.getElementById('toggleSidebarBtnCollapsed');
            if (toggleSidebarBtnCollapsed) {
                toggleSidebarBtnCollapsed.style.display = sidebar.classList.contains('collapsed') ? 'block' : 'none';
            }
        });
    }

    const toggleSidebarBtnCollapsed = document.getElementById('toggleSidebarBtnCollapsed');
    if (toggleSidebarBtnCollapsed) {
        toggleSidebarBtnCollapsed.addEventListener('click', () => {
            const sidebar = document.getElementById('sidebar');
            sidebar.classList.remove('collapsed');
            const toggleSidebarBtn = document.getElementById('toggleSidebarBtn');
            if (toggleSidebarBtn) {
                toggleSidebarBtn.textContent = 'Collapse';
            }
            toggleSidebarBtnCollapsed.style.display = 'none';
        });
    }

    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
            button.classList.add('active');
            const tabContent = document.getElementById(button.dataset.tab);
            if (tabContent) {
                tabContent.style.display = 'block';
            }
        });
    });

    const saveConfigBtn = document.getElementById('saveConfigBtn');
    if (saveConfigBtn) {
        saveConfigBtn.addEventListener('click', () => {
            const personaName = document.getElementById('personaName') ? document.getElementById('personaName').value.trim() : '';
            const personaRole = document.getElementById('personaRole') ? document.getElementById('personaRole').value.trim() : '';
            const channelName = document.getElementById('modalChannelName') ? document.getElementById('modalChannelName').value.trim() : '';
            const token = document.getElementById('modalToken') ? document.getElementById('modalToken').value.trim() : '';
            const clientId = document.getElementById('modalClientId') ? document.getElementById('modalClientId').value.trim() : '';
            const extraDelayListener = document.getElementById('modalExtraDelayListener') ? document.getElementById('modalExtraDelayListener').value.trim() : '';
            const nbSpamMessage = document.getElementById('modalNbSpamMessage') ? document.getElementById('modalNbSpamMessage').value.trim() : '';
            const prePrompt = document.getElementById('prePrompt') ? document.getElementById('prePrompt').value.trim() : '';
            const ollamaModel = document.getElementById('ollamaModel') ? document.getElementById('ollamaModel').value.trim() : '';
            const avatarModel = document.getElementById('avatarModel') ? document.getElementById('avatarModel').value.trim() : '';
            const backgroundImage = document.getElementById('backgroundImage') ? document.getElementById('backgroundImage').value.trim() : '';
            const botNameFollowSub = document.getElementById('modalBotNameFollowSub') ? document.getElementById('modalBotNameFollowSub').value.trim() : '';
            const keyWordFollow = document.getElementById('modalKeyWordFollow') ? document.getElementById('modalKeyWordFollow').value.trim() : '';
            const keyWordSub = document.getElementById('modalKeyWordSub') ? document.getElementById('modalKeyWordSub').value.trim() : '';
            const delimiterName = document.getElementById('modalDelimiterName') ? document.getElementById('modalDelimiterName').value.trim() : '';
            const delimiterNameEnd = document.getElementById('modalDelimiterNameEnd') ? document.getElementById('modalDelimiterNameEnd').value.trim() : '';

            // Save configuration to .env file
            const config = {
                PERSONA_NAME: personaName,
                PERSONA_ROLE: personaRole,
                PRE_PROMPT: prePrompt,
                AVATAR_MODEL: avatarModel,
                BACKGROUND_IMAGE: backgroundImage,
                CHANNEL_NAME: channelName,
                TOKEN: token,
                CLIENT_ID: clientId,
                EXTRA_DELAY_LISTENER: extraDelayListener,
                NB_SPAM_MESSAGE: nbSpamMessage,
                OLLAMA_MODEL: ollamaModel,
                BOT_NAME_FOLLOW_SUB: botNameFollowSub,
                KEY_WORD_FOLLOW: keyWordFollow,
                KEY_WORD_SUB: keyWordSub,
                DELIMITER_NAME: delimiterName,
                DELIMITER_NAME_END: delimiterNameEnd
            };
            socket.emit('save_config', config);
        });
    }

    const avatarModelSelect = document.getElementById('avatarModel');
    const backgroundImageSelect = document.getElementById('backgroundImage');

    // Populate avatar models
    fetch('/get_avatar_models')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    avatarModelSelect.appendChild(option);
                });
            } else {
                console.error('Failed to load avatar models:', data.message);
            }
        })
        .catch(error => console.error('Error fetching avatar models:', error));

    // Populate background images
    fetch('/get_background_images')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                data.images.forEach(image => {
                    const option = document.createElement('option');
                    option.value = image;
                    option.textContent = image;
                    backgroundImageSelect.appendChild(option);
                });

                // Set the background image select value after options are populated
                const backgroundImage = data.BACKGROUND_IMAGE || '';
                if (backgroundImage) {
                    backgroundImageSelect.value = backgroundImage;
                    document.body.style.backgroundImage = `url('/static/images/background/${backgroundImage}')`;
                    document.body.style.backgroundPosition = 'center';
                    document.body.style.backgroundSize = 'cover';
                }
            } else {
                console.error('Failed to load background images:', data.message);
            }
        })
        .catch(error => console.error('Error fetching background images:', error));

    // Update background image on change
    if (backgroundImageSelect) {
        backgroundImageSelect.addEventListener('change', function() {
            const selectedImage = backgroundImageSelect.value;
            document.body.style.backgroundImage = `url('/static/images/background/${selectedImage}')`;
            document.body.style.backgroundPosition = 'center';
            document.body.style.backgroundSize = 'cover';
        });
    }

    // Load new avatar model on change
    if (avatarModelSelect) {
        avatarModelSelect.addEventListener('change', function() {
            const selectedModel = avatarModelSelect.value;
            let modelPath;
            if (selectedModel === 'mao_pro') {
                modelPath = `models/${selectedModel}/mao_pro.model3.json`;
            } else if (selectedModel === 'haru') {
                modelPath = `models/${selectedModel}/haru_greeter_t03.model3.json`;
            } else {
                modelPath = `models/${selectedModel}/${selectedModel}.model.json`;
            }
            loadAvatarModel(modelPath);
        });
    }

    const tokenField = document.getElementById('token');
    if (tokenField) {
        tokenField.classList.add('blurry');

        tokenField.addEventListener('focus', () => {
            tokenField.classList.remove('blurry');
        });

        tokenField.addEventListener('blur', () => {
            tokenField.classList.add('blurry');
        });
    }

    const clientIdField = document.getElementById('clientId');
    if (clientIdField) {
        clientIdField.classList.add('blurry');

        clientIdField.addEventListener('focus', () => {
            clientIdField.classList.remove('blurry');
        });

        clientIdField.addEventListener('blur', () => {
            clientIdField.classList.add('blurry');
        });
    }

    const configBtn = document.getElementById('configBtn');
    if (configBtn) {
        configBtn.addEventListener('click', () => {
            const modal = document.getElementById('configModal');
            modal.style.display = 'block';
        });
    }

    const closeModalBtn = document.querySelector('.close');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', () => {
            const modal = document.getElementById('configModal');
            modal.style.display = 'none';
        });
    }

    window.addEventListener('click', (event) => {
        const modal = document.getElementById('configModal');
        if (event.target === modal) {
            modal.style.display = 'none';
        }
    });

    const saveModalConfigBtn = document.getElementById('saveModalConfigBtn');
    if (saveModalConfigBtn) {
        saveModalConfigBtn.addEventListener('click', () => {
            const extraDelayListener = document.getElementById('modalExtraDelayListener') ? document.getElementById('modalExtraDelayListener').value.trim() : '';
            const nbSpamMessage = document.getElementById('modalNbSpamMessage') ? document.getElementById('modalNbSpamMessage').value.trim() : '';
            const botNameFollowSub = document.getElementById('modalBotNameFollowSub') ? document.getElementById('modalBotNameFollowSub').value.trim() : '';
            const keyWordFollow = document.getElementById('modalKeyWordFollow') ? document.getElementById('modalKeyWordFollow').value.trim() : '';
            const keyWordSub = document.getElementById('modalKeyWordSub') ? document.getElementById('modalKeyWordSub').value.trim() : '';
            const delimiterName = document.getElementById('modalDelimiterName') ? document.getElementById('modalDelimiterName').value.trim() : '';
            const delimiterNameEnd = document.getElementById('modalDelimiterNameEnd') ? document.getElementById('modalDelimiterNameEnd').value.trim() : '';
            const channelName = document.getElementById('modalChannelName') ? document.getElementById('modalChannelName').value.trim() : '';
            const token = document.getElementById('modalToken') ? document.getElementById('modalToken').value.trim() : '';
            const clientId = document.getElementById('modalClientId') ? document.getElementById('modalClientId').value.trim() : '';

            // Update the main configuration fields
            if (document.getElementById('extraDelayListener')) document.getElementById('extraDelayListener').value = extraDelayListener;
            if (document.getElementById('nbSpamMessage')) document.getElementById('nbSpamMessage').value = nbSpamMessage;
            if (document.getElementById('botNameFollowSub')) document.getElementById('botNameFollowSub').value = botNameFollowSub;
            if (document.getElementById('keyWordFollow')) document.getElementById('keyWordFollow').value = keyWordFollow;
            if (document.getElementById('keyWordSub')) document.getElementById('keyWordSub').value = keyWordSub;
            if (document.getElementById('delimiterName')) document.getElementById('delimiterName').value = delimiterName;
            if (document.getElementById('delimiterNameEnd')) document.getElementById('delimiterNameEnd').value = delimiterNameEnd;
            if (document.getElementById('channelName')) document.getElementById('channelName').value = channelName;
            if (document.getElementById('token')) document.getElementById('token').value = token;
            if (document.getElementById('clientId')) document.getElementById('clientId').value = clientId;

            // Save configuration to .env file
            const config = {
                EXTRA_DELAY_LISTENER: extraDelayListener,
                NB_SPAM_MESSAGE: nbSpamMessage,
                BOT_NAME_FOLLOW_SUB: botNameFollowSub,
                KEY_WORD_FOLLOW: keyWordFollow,
                KEY_WORD_SUB: keyWordSub,
                DELIMITER_NAME: delimiterName,
                DELIMITER_NAME_END: delimiterNameEnd,
                CHANNEL_NAME: channelName,
                TOKEN: token,
                CLIENT_ID: clientId
            };
            socket.emit('save_config', config);

            // Close the modal
            const modal = document.getElementById('configModal');
            modal.style.display = 'none';
        });
    }
}

function showQuestionDisplay(text) {
    const questionDisplay = document.getElementById('question-display');
    questionDisplay.textContent = text;
    questionDisplay.style.display = 'block';
    clearTimeout(questionDisplay.hideTimeout);
    questionDisplay.hideTimeout = setTimeout(() => {
        questionDisplay.style.display = 'none';
    }, 10000);
}

function populateOllamaModels() {
    fetch('/get_ollama_models')
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                const select = document.getElementById('ollamaModel');
                data.models.forEach(model => {
                    const option = document.createElement('option');
                    option.value = model;
                    option.textContent = model;
                    select.appendChild(option);
                });
            } else {
                console.error('Failed to load Ollama models:', data.message);
            }
        })
        .catch(error => console.error('Error fetching Ollama models:', error));
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
    const notification = document.getElementById('notification');
    notification.textContent = message;
    notification.className = `notification ${type}`;

    // Show notification
    setTimeout(() => {
        notification.classList.add('show');
    }, 100);

    // Hide notification after 3 seconds
    setTimeout(() => {
        notification.classList.remove('show');
    }, 3000);
}

// Socket event listeners
socket.on('speak_text', data => speak(data.text));
socket.on('model_path', data => {
    modelPath = data.path;
    console.log("Received model path:", modelPath);
    main(modelPath);
});
socket.on('ai_response', data => speak(data.text));
socket.on('display_question', showQuestionDisplay);
socket.on('fireworks', triggerFireworks);
socket.on('connect', () => console.log('WebSocket connected:', socket.id));
socket.on('disconnect', () => console.log('WebSocket disconnected'));

socket.on('load_config', data => {
    if (data.PERSONA_NAME) document.getElementById('personaName').value = data.PERSONA_NAME;
    if (data.PERSONA_ROLE) document.getElementById('personaRole').value = data.PERSONA_ROLE;
    if (data.PRE_PROMPT) document.getElementById('prePrompt').value = data.PRE_PROMPT;
    if (data.AVATAR_MODEL) document.getElementById('avatarModel').value = data.AVATAR_MODEL;
    if (data.OLLAMA_MODEL) document.getElementById('ollamaModel').value = data.OLLAMA_MODEL;
    if (data.CHANNEL_NAME) document.getElementById('modalChannelName').value = data.CHANNEL_NAME;
    if (data.TOKEN) document.getElementById('modalToken').value = data.TOKEN;
    if (data.CLIENT_ID) document.getElementById('modalClientId').value = data.CLIENT_ID;
    if (data.EXTRA_DELAY_LISTENER) document.getElementById('modalExtraDelayListener').value = data.EXTRA_DELAY_LISTENER;
    if (data.NB_SPAM_MESSAGE) document.getElementById('modalNbSpamMessage').value = data.NB_SPAM_MESSAGE;
    if (data.BOT_NAME_FOLLOW_SUB) document.getElementById('modalBotNameFollowSub').value = data.BOT_NAME_FOLLOW_SUB;
    if (data.KEY_WORD_FOLLOW) document.getElementById('modalKeyWordFollow').value = data.KEY_WORD_FOLLOW;
    if (data.KEY_WORD_SUB) document.getElementById('modalKeyWordSub').value = data.KEY_WORD_SUB;
    if (data.DELIMITER_NAME) document.getElementById('modalDelimiterName').value = data.DELIMITER_NAME;
    if (data.DELIMITER_NAME_END) document.getElementById('modalDelimiterNameEnd').value = data.DELIMITER_NAME_END;
    if (data.BACKGROUND_IMAGE) document.getElementById('backgroundImage').value = data.BACKGROUND_IMAGE;

    if (data.AVATAR_MODEL) {
        let modelPath;
        if (data.AVATAR_MODEL === 'mao_pro') {
            modelPath = `models/${data.AVATAR_MODEL}/mao_pro.model3.json`;
        } else if (data.AVATAR_MODEL === 'haru') {
            modelPath = `models/${data.AVATAR_MODEL}/haru_greeter_t03.model3.json`;
        } else {
            modelPath = `models/${data.AVATAR_MODEL}/${data.AVATAR_MODEL}.model.json`;
        }
        loadAvatarModel(modelPath);
    }

    if (data.BACKGROUND_IMAGE) {
        document.body.style.backgroundImage = `url('/static/images/background/${data.BACKGROUND_IMAGE}')`;
        document.body.style.backgroundPosition = 'center';
        document.body.style.backgroundSize = 'cover';
    }
});

socket.on('save_config_response', function(response) {
    if (response.status === 'success') {
        showNotification('success', 'Configuration saved successfully');
    } else {
        showNotification('error', response.message);
    }
});

function applyConfig(config) {
    document.getElementById('avatarModel').value = config.AVATAR_MODEL || '';
    document.getElementById('personaName').value = config.PERSONA_NAME || '';
    document.getElementById('personaRole').value = config.PERSONA_ROLE || '';
    document.getElementById('prePrompt').value = config.PRE_PROMPT || '';
    document.getElementById('backgroundImage').value = config.BACKGROUND_IMAGE || '';

    if (config.BACKGROUND_IMAGE) {
        document.body.style.backgroundImage = `url('/static/images/background/${config.BACKGROUND_IMAGE}')`;
        document.body.style.backgroundPosition = 'center';
        document.body.style.backgroundSize = 'cover';
    }

    if (config.AVATAR_MODEL) {
        if (config.AVATAR_MODEL === 'mao_pro') {
            modelPath = `models/${config.AVATAR_MODEL}/mao_pro.model3.json`;
        } else if (config.AVATAR_MODEL === 'haru') {
            modelPath = `models/${config.AVATAR_MODEL}/haru_greeter_t03.model3.json`;
        } else {
            modelPath = `models/${config.AVATAR_MODEL}/${config.AVATAR_MODEL}.model.json`;
        }
        loadAvatarModel(modelPath);
    }
}

socket.on('load_config', config => {
    console.log("Loaded config:", config);  // Debugging line
    applyConfig(config);
});

function updateListenerStatus(status) {
    const statusText = document.getElementById('listenerStatusText');
    statusText.textContent = status ? 'Running' : 'Stopped';
    statusText.style.color = status ? 'green' : 'red';
}

function checkListenerStatus() {
    fetch('/listener_status')
        .then(response => response.json())
        .then(data => {
            updateListenerStatus(data.status === 'running');
        });
}

document.getElementById('startListenerBtn').addEventListener('click', () => {
    fetch('/start_listener', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateListenerStatus(true);
            } else {
                alert('Failed to start listener: ' + data.message);
            }
        });
});

document.getElementById('stopListenerBtn').addEventListener('click', () => {
    fetch('/stop_listener', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                updateListenerStatus(false);
            } else {
                alert('Failed to stop listener: ' + data.message);
            }
        });
});

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
    setupEventListeners();
    socket.connect();
    socket.emit('request_model_path');
    populateOllamaModels();
    socket.emit('load_config');
    checkListenerStatus(); // Check listener status on page load
});