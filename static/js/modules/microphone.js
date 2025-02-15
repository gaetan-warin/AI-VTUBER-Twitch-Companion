import { showNotification, askAIRequest } from './ui.js';

export let microphonePermissionState = 'prompt';
let isRecording = false;
let audioContext, audioInput, analyser;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;

// Update socket configuration to fake browser to use default webkitSpeechRecognition
const socket = io('http://localhost:3000', {
    transports: ['websocket', 'polling'],
    reconnectionAttempts: MAX_RECONNECT_ATTEMPTS,
    reconnectionDelay: 1000,
    timeout: 10000
});
let serverReady = false;

export function initializeMicrophone() {
    setupMicrophoneAccess();
    checkMicrophoneAccess();
    setupSpeechSocket();
}

function setupSpeechSocket() {
    socket.on('connect', () => {
        console.log('[Speech Socket] Connected to speech recognition server');
        reconnectAttempts = 0;
        serverReady = true;
        $('#startRecordingBtn').prop('disabled', false);
    });

    socket.on('speechServerStatus', (data) => {
        console.log('[Speech Socket] Server status:', data.status);
        serverReady = data.status === 'ready';
        if (serverReady) {
            console.log('[Speech Socket] Speech server is ready');
            $('#startRecordingBtn').prop('disabled', false);
        }
    });

    socket.on('connect_error', (error) => {
        console.error('[Speech Socket] Connection error:', error);
        reconnectAttempts++;
        serverReady = false;
        $('#startRecordingBtn').prop('disabled', true);

        if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
            showNotification('error', 'Failed to connect to speech server. Please refresh the page.');
            socket.disconnect();
        } else {
            showNotification('warning', `Reconnecting to speech server... (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
        }
    });

    socket.on('error', (error) => {
        console.error('[Speech Socket] Server error:', error);
        showNotification('error', error.message || 'Speech recognition server error');
    });

    socket.on('speechData', (text) => {
        console.log('[Speech Socket] Received speech data:', text);

        if (text && isRecording) {
            const isWakeWordEnabled = $('#wakeWordEnabled').is(':checked');
            const wakeWord = $('#wakeWord').val().trim().toLowerCase();

            console.log('[Speech Process] Wake word enabled:', isWakeWordEnabled);
            console.log('[Speech Process] Wake word:', wakeWord);

            if (!isWakeWordEnabled || (wakeWord && isWakeWordDetected(text.toLowerCase(), wakeWord))) {
                console.log('[Speech Process] Processing speech with AI');
                handleMicrophoneAIRequest(text, $('#fixedLanguage').val());
            } else {
                console.log('[Speech Process] Wake word not detected, ignoring input');
            }
        }
    });
}

export function startRecording() {
    if (!serverReady) {
        showNotification('error', 'Speech recognition server is not ready');
        return;
    }

    if (isRecording) return;

    navigator.mediaDevices.getUserMedia({ audio: true })
        .then(stream => {
            isRecording = true;
            $('#startRecordingBtn').text('Stop Recording').addClass('recording');

            if ($('#waveToggle').is(':checked')) {
                $('#waveCanvas').show();
                initializeWaveVisualization(stream);
            }

            const lang = getLangCode($('#fixedLanguage').val());
            socket.emit('startSpeech', { lang });
            showNotification('info', 'Recording started. Speak now.');
        })
        .catch(err => {
            console.error('Error accessing microphone:', err);
            showNotification('error', 'Error accessing microphone');
        });
}

export function stopRecording() {
    if (!isRecording) return;

    isRecording = false;
    $('#startRecordingBtn').text('Start Recording').removeClass('recording');
    $('#waveCanvas').hide();

    if (audioContext) {
        audioContext.close();
        audioContext = null;
    }
}

export function setupMicrophoneAccess() {
    $('#requestMicrophoneAccess').on('click', () => {
        if (microphonePermissionState === 'denied') {
            alert('Please enable microphone access in your browser settings and reload the page.');
            return;
        }

        navigator.mediaDevices.getUserMedia({ audio: true })
            .then(stream => {
                stream.getTracks().forEach(track => track.stop());
                microphonePermissionState = 'granted';
                $('#microphoneOverlay').hide();
            })
            .catch(err => {
                console.error('Failed to get microphone access:', err);
                microphonePermissionState = 'denied';
                $('#microphoneOverlay p').text('Microphone access was denied. Please enable it in your browser settings.');
            });
    });
}

export function checkMicrophoneAccess() {
    $('#microphoneOverlay').show();

    navigator.permissions.query({ name: 'microphone' })
        .then(permissionStatus => {
            microphonePermissionState = permissionStatus.state;

            if (permissionStatus.state === 'granted') {
                $('#microphoneOverlay').hide();
                updateCurrentMicrophone();
            } else {
                $('#microphoneOverlay').show();
                if (permissionStatus.state === 'prompt') {
                    $('#microphoneOverlay p').text('Microphone access is required for this feature');
                } else {
                    $('#microphoneOverlay p').text('Microphone access was denied. Please enable it in your browser settings.');
                }
            }

            permissionStatus.onchange = () => {
                microphonePermissionState = permissionStatus.state;
                if (permissionStatus.state === 'granted') {
                    $('#microphoneOverlay').hide();
                    updateCurrentMicrophone();
                } else {
                    $('#microphoneOverlay').show();
                    $('#microphoneOverlay p').text('Microphone access was denied. Please enable it in your browser settings.');
                }
            };
        })
        .catch(err => {
            console.error('Error checking microphone permission:', err);
            $('#microphoneOverlay').show();
        });
}

function updateCurrentMicrophone() {
    navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            const audioDevices = devices.filter(device => device.kind === 'audioinput');
            if (audioDevices.length > 0) {
                const defaultDevice = audioDevices.find(device => device.deviceId === 'default')
                    || audioDevices.find(device => device.label.toLowerCase().includes('default'))
                    || audioDevices[0];

                $('#currentMicrophone').val(defaultDevice.label || 'Default Microphone');
            } else {
                $('#currentMicrophone').val('No microphone detected');
            }
        })
        .catch(err => {
            console.error('Error accessing media devices:', err);
            $('#currentMicrophone').val('Unable to detect microphone');
        });
}

function getLangCode(lang) {
    const langCodes = {
        'en': 'en-US',
        'fr': 'fr-FR',
        'es': 'es-ES',
        'de': 'de-DE',
        'it': 'it-IT',
        'ja': 'ja-JP',
        'ko': 'ko-KR',
        'zh': 'zh-CN',
        'ru': 'ru-RU'
    };
    return langCodes[lang] || 'en-US';
}

function isWakeWordDetected(text, wakeWord) {
    const normalizedText = text.replace(/[.,!?]/g, '').toLowerCase();
    const normalizedWakeWord = wakeWord.replace(/[.,!?]/g, '').toLowerCase();
    const wakeWordParts = normalizedWakeWord.split(' ');

    return wakeWordParts.length > 1 ?
        normalizedText.includes(normalizedWakeWord) :
        new RegExp(`\\b${normalizedWakeWord}\\b`).test(normalizedText);
}

function handleMicrophoneAIRequest(text, selectedLanguage) {
    console.log('[Speech AI] Sending request to AI:', { text, language: selectedLanguage });
    askAIRequest({
        text,
        source: 'microphone',
        fixedLanguage: selectedLanguage
    });
}

function initializeWaveVisualization(stream) {
    if (!stream) {
        console.error('No audio stream provided');
        return;
    }

    try {
        // Create new audio context
        audioContext = new (window.AudioContext || window.webkitAudioContext)();

        // Create audio source from stream
        audioInput = audioContext.createMediaStreamSource(stream);

        // Create analyser node
        analyser = audioContext.createAnalyser();
        analyser.fftSize = 256;

        // Connect nodes
        audioInput.connect(analyser);

        // Start drawing
        drawSpectrum(analyser);
        console.log('Wave visualization initialized');
    } catch (err) {
        console.error('Wave visualization error:', err);
    }
}

function drawSpectrum(analyser) {
    const canvas = document.getElementById('waveCanvas');
    const ctx = canvas.getContext('2d');
    const WIDTH = canvas.width;
    const HEIGHT = canvas.height;

    analyser.fftSize = 256;
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    ctx.clearRect(0, 0, WIDTH, HEIGHT);

    function draw() {
        requestAnimationFrame(draw);

        analyser.getByteFrequencyData(dataArray);

        ctx.fillStyle = 'rgb(0, 0, 0)';
        ctx.fillRect(0, 0, WIDTH, HEIGHT);

        const barWidth = (WIDTH / bufferLength) * 2.5;
        let barHeight;
        let x = 0;

        for (let i = 0; i < bufferLength; i++) {
            barHeight = dataArray[i] / 2;

            ctx.fillStyle = `rgb(${barHeight + 100},50,50)`;
            ctx.fillRect(x, HEIGHT - barHeight / 2, barWidth, barHeight);

            x += barWidth + 1;
        }
    }

    draw();
}

export function isCurrentlyRecording() {
    return isRecording;
}
