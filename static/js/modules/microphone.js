import { askAI } from './socket.js';
import { areVoicesReady } from './speech.js';
import { showNotification } from './ui.js';
import { detectLanguage } from './languageDetection.js';

export let microphonePermissionState = 'prompt';
let recognition = null;
let isRecording = false;
let audioContext, audioInput, analyser;
let recognitionTimeout;

export function initializeMicrophone() {
    setupMicrophoneAccess();
    checkMicrophoneAccess();
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

export function startRecording() {
    if (!areVoicesReady()) {
        showNotification('warning', "Speech synthesis voices are not loaded yet. Please wait a moment and try again.");
        return;
    }
    if (!recognition) initializeSpeechRecognition();
    
    if (isRecording) {
        console.log('Recording is already in progress');
        return;
    }

    navigator.mediaDevices.getUserMedia({ 
        audio: { 
            echoCancellation: true,
            noiseSuppression: true,
            autoGainControl: true 
        } 
    })
    .then(stream => {
        initializeWaveVisualization(stream);
        try {
            recognition.start();
            isRecording = true;
            $('#startRecordingBtn').text('Stop Recording').addClass('recording');
            
            if ($('#waveToggle').is(':checked')) {
                $('#waveCanvas').show();
            }

            showNotification('info', 'Recording started. Speak now.');

            // Set a timeout to stop and restart recognition if no speech is detected
            recognitionTimeout = setTimeout(() => {
                if (isRecording) {
                    recognition.stop();
                    showNotification('warning', 'No speech detected. Restarting...');
                }
            }, 10000); // 10 seconds timeout
        } catch (error) {
            console.error('Error starting speech recognition:', error);
            showNotification('error', 'Failed to start speech recognition. Please try again.');
        }
    })
    .catch(err => {
        console.error('Microphone access denied:', err);
        showNotification('error', 'Failed to access the microphone. Please check your permissions.');
    });
}

export function stopRecording() {
    if (recognition && isRecording) {
        try {
            recognition.stop();
        } catch (error) {
            console.error('Error stopping speech recognition:', error);
        }
        isRecording = false;
        $('#startRecordingBtn').text('Start Recording').removeClass('recording');
        $('#waveCanvas').hide();

        if (audioContext) {
            audioContext.close();
            audioContext = null;
        }

        clearTimeout(recognitionTimeout);
    }
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

function initializeSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window)) {
        showNotification('error', 'Speech recognition is not supported in this browser.');
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.continuous = false; // Changed to false to better handle language switching
    recognition.interimResults = true;
    
    // Initial language setup
    const selectedLanguage = $('#fixedLanguage').val();
    recognition.lang = selectedLanguage === 'auto' ? navigator.language || 'en-US' : getLangCode(selectedLanguage);

    recognition.onstart = () => {
        console.log('Speech recognition started with language:', recognition.lang);
        showNotification('info', 'Listening... Speak now');
    };

    recognition.onresult = (event) => {
        clearTimeout(recognitionTimeout);
        const result = event.results[event.results.length - 1];
        
        if (result.isFinal) {
            const text = result[0].transcript;
            console.log('Speech recognized:', text);
            
            if (text.trim()) {
                const selectedLanguage = $('#fixedLanguage').val();
                if (selectedLanguage === 'auto') {
                    const detectedLang = detectLanguage(text);
                    const newLangCode = getLangCode(detectedLang);
                    
                    if (newLangCode !== recognition.lang) {
                        console.log(`Switching recognition language from ${recognition.lang} to ${newLangCode}`);
                        recognition.lang = newLangCode;
                        restartRecognition();
                    }
                }
                askAI(text);
            }
        }
    };

    recognition.onend = () => {
        console.log('Speech recognition ended');
        clearTimeout(recognitionTimeout);
        if (isRecording) {
            restartRecognition();
        }
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error:', event.error);
        if (event.error === 'no-speech') {
            console.log('No speech detected, continuing to listen...');
            showNotification('warning', 'No speech detected. Please try speaking again.');
        } else {
            showNotification('error', `Speech recognition error: ${event.error}`);
        }
        if (event.error === 'no-speech' || event.error === 'audio-capture') {
            // Do nothing, let the onend event handler restart recognition
        } else {
            stopRecording();
        }
    };
}

function restartRecognition() {
    try {
        setTimeout(() => {
            if (isRecording) {
                recognition.start();
                console.log('Restarting speech recognition with language:', recognition.lang);
                recognitionTimeout = setTimeout(() => {
                    if (isRecording) {
                        recognition.stop();
                        showNotification('warning', 'No speech detected. Restarting...');
                    }
                }, 10000);
            }
        }, 100);
    } catch (error) {
        console.error('Error restarting speech recognition:', error);
        handleRecognitionError(error);
    }
}

function handleRecognitionError(error) {
    isRecording = false;
    $('#startRecordingBtn').text('Start Recording').removeClass('recording');
    showNotification('error', 'Speech recognition error. Please try again.');
    console.error('Recognition error:', error);
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

function initializeWaveVisualization(stream) {
    if (!stream) {
        console.error('No audio stream provided');
        return;
    }

    audioContext = new (window.AudioContext || window.webkitAudioContext)();
    audioInput = audioContext.createMediaStreamSource(stream);
    analyser = audioContext.createAnalyser();
    audioInput.connect(analyser);

    drawSpectrum(analyser);
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

        for(let i = 0; i < bufferLength; i++) {
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
