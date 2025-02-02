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
        if (isSpeaking) {
            mouthState.value = Math.sin(performance.now() / 200) / 2 + 0.5;
            
            if (currentModel?.internalModel?.coreModel) {
                try {
                    currentModel.internalModel.coreModel.setParamFloat(
                        'PARAM_MOUTH_OPEN_Y', 
                        mouthState.value
                    );
                } catch (error) {
                    console.error('Mouth parameter update failed:', error);
                }
            }
        }
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

        // Log available parameters for debugging

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
    document.getElementById('speakBtn').addEventListener('click', () => {
        const inputField = document.getElementById('makeItSpeak');
        const text = inputField.value.trim();
        if (text) {
            socket.emit('speak', { text });
            inputField.value = ''; // Clear the input field
        }
    });

    document.getElementById('askAIBtn').addEventListener('click', () => {
        const inputField = document.getElementById('makeItSpeak');
        const text = inputField.value.trim();
        if (text) {
            askAI(text);
            inputField.value = ''; // Clear the input field
        }
    });

    document.getElementById('makeItSpeak').addEventListener('keydown', (event) => {
        if (event.ctrlKey && event.key === 'Enter') {
            const inputField = event.target;
            const text = inputField.value.trim();
            if (text) {
                socket.emit('speak', { text });
                inputField.value = ''; // Clear the input field
            }
        }
    });

    document.getElementById('toggleSidebarBtn').addEventListener('click', () => {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.toggle('collapsed');
        document.getElementById('toggleSidebarBtn').textContent = sidebar.classList.contains('collapsed') ? 'Expand' : 'Collapse';
        document.getElementById('toggleSidebarBtnCollapsed').style.display = sidebar.classList.contains('collapsed') ? 'block' : 'none';
    });

    document.getElementById('toggleSidebarBtnCollapsed').addEventListener('click', () => {
        const sidebar = document.getElementById('sidebar');
        sidebar.classList.remove('collapsed');
        document.getElementById('toggleSidebarBtn').textContent = 'Collapse';
        document.getElementById('toggleSidebarBtnCollapsed').style.display = 'none';
    });

    document.querySelectorAll('.tab-button').forEach(button => {
        button.addEventListener('click', () => {
            document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(content => content.style.display = 'none');
            button.classList.add('active');
            document.getElementById(button.dataset.tab).style.display = 'block';
        });
    });

    document.getElementById('saveConfigBtn').addEventListener('click', () => {
        const personaName = document.getElementById('personaName').value.trim();
        const personaRole = document.getElementById('personaRole').value.trim();
        const channelName = document.getElementById('channelName').value.trim();
        const token = document.getElementById('token').value.trim();
        const clientId = document.getElementById('clientId').value.trim();
        const extraDelayListener = document.getElementById('extraDelayListener').value.trim();
        const nbSpamMessage = document.getElementById('nbSpamMessage').value.trim();
        const prePrompt = document.getElementById('prePrompt').value.trim();
        const ollamaModel = document.getElementById('ollamaModel').value.trim();
        const avatarModel = document.getElementById('avatarModel').value.trim();
        const backgroundImage = document.getElementById('backgroundImage').value.trim();
        const botNameFollowSub = document.getElementById('botNameFollowSub').value.trim();
        const keyWordFollow = document.getElementById('keyWordFollow').value.trim();
        const keyWordSub = document.getElementById('keyWordSub').value.trim();
        const delimiterName = document.getElementById('delimiterName').value.trim();
        const delimiterNameEnd = document.getElementById('delimiterNameEnd').value.trim();

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
    backgroundImageSelect.addEventListener('change', function() {
        const selectedImage = backgroundImageSelect.value;
        document.body.style.backgroundImage = `url('/static/images/background/${selectedImage}')`;
        document.body.style.backgroundPosition = 'center';
        document.body.style.backgroundSize = 'cover';
    });

    // Load new avatar model on change
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
    document.getElementById('personaName').value = data.PERSONA_NAME || '';
    document.getElementById('personaRole').value = data.PERSONA_ROLE || '';
    document.getElementById('prePrompt').value = data.PRE_PROMPT || '';
    document.getElementById('avatarModel').value = data.AVATAR_MODEL || '';
    document.getElementById('channelName').value = data.CHANNEL_NAME || '';
    document.getElementById('token').value = data.TOKEN || '';
    document.getElementById('clientId').value = data.CLIENT_ID || '';
    document.getElementById('extraDelayListener').value = data.EXTRA_DELAY_LISTENER || '';
    document.getElementById('nbSpamMessage').value = data.NB_SPAM_MESSAGE || '';
    document.getElementById('ollamaModel').value = data.OLLAMA_MODEL || '';
    document.getElementById('botNameFollowSub').value = data.BOT_NAME_FOLLOW_SUB || '';
    document.getElementById('keyWordFollow').value = data.KEY_WORD_FOLLOW || '';
    document.getElementById('keyWordSub').value = data.KEY_WORD_SUB || '';
    document.getElementById('delimiterName').value = data.DELIMITER_NAME || '';
    document.getElementById('delimiterNameEnd').value = data.DELIMITER_NAME_END || '';
    document.getElementById('backgroundImage').value = data.BACKGROUND_IMAGE || '';

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

// Initial setup
document.addEventListener('DOMContentLoaded', () => {
    
    setupEventListeners();
    socket.connect();
    socket.emit('request_model_path');
    populateOllamaModels();
    socket.emit('load_config');

    socket.on('load_config', config => {
        console.log("Loaded config:", config);  // Debugging line
        document.getElementById('avatarModel').value = config.AVATAR_MODEL || '';
        document.getElementById('personaName').value = config.PERSONA_NAME || '';
        document.getElementById('personaRole').value = config.PERSONA_ROLE || '';
        document.getElementById('prePrompt').value = config.PRE_PROMPT || '';
        document.getElementById('backgroundImage').value = config.BACKGROUND_IMAGE || '';

        if (config.BACKGROUND_IMAGE) {
            document.body.classList.add('dynamic-background');
            document.body.style.backgroundImage = `url('/static/images/background/${config.BACKGROUND_IMAGE}')`;
        }
    });

    socket.on('load_config_error', error => {
        console.error('Error loading config:', error.message);
    });
});