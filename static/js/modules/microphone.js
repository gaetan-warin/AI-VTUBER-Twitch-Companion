import { askAI } from './socket.js';
import { areVoicesReady } from './speech.js';

export let microphonePermissionState = 'prompt';
let recognition = null;
let isRecording = false;
let audioContext, audioInput, analyser;

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
                updateMicrophoneList();
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
                    updateMicrophoneList();
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
                
                updateMicrophoneList().then(() => {
                    navigator.mediaDevices.enumerateDevices().then(devices => {
                        const audioDevices = devices.filter(device => device.kind === 'audioinput');
                        if (audioDevices.length > 0) {
                            const defaultDevice = audioDevices.find(device => device.deviceId === 'default') 
                                             || audioDevices.find(device => device.label.toLowerCase().includes('default'))
                                             || audioDevices[0];
                            
                            $('#preferredMicrophone').val(defaultDevice.deviceId);
                        }
                    });
                });
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
        alert("Speech synthesis voices are not loaded yet. Please wait a moment and try again.");
        return;
    }
    if (!recognition) initializeSpeechRecognition();
    const selectedMicrophoneId = $('#preferredMicrophone').val();
    
    navigator.mediaDevices.getUserMedia({ 
        audio: { deviceId: selectedMicrophoneId ? { exact: selectedMicrophoneId } : undefined } 
    })
    .then(stream => {
        initializeWaveVisualization(stream);
        recognition.start();
        isRecording = true;
        $('#startRecordingBtn').text('Stop Recording').addClass('recording');
        
        if ($('#waveToggle').is(':checked')) {
            $('#waveCanvas').show();
        }
    })
    .catch(err => {
        console.error('Microphone access denied:', err);
        alert('Failed to access the microphone. Please check your permissions.');
    });
}

export function stopRecording() {
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

export function updateMicrophoneList() {
    const micSelect = $('#preferredMicrophone');
    const currentSelection = micSelect.val();
    micSelect.empty();

    return navigator.mediaDevices.enumerateDevices()
        .then(devices => {
            const audioDevices = devices.filter(device => device.kind === 'audioinput');
            if (audioDevices.length === 0) {
                $('#microphoneOverlay').show();
                return;
            }

            audioDevices.forEach(device => {
                micSelect.append(new Option(device.label || `Microphone ${micSelect.children().length + 1}`, device.deviceId));
            });
            
            if (currentSelection && micSelect.find(`option[value="${currentSelection}"]`).length) {
                micSelect.val(currentSelection);
            }
        })
        .catch(err => {
            console.error('Error accessing media devices:', err);
            $('#microphoneOverlay').show();
            throw err;
        });
}

function initializeSpeechRecognition() {
    if (!('webkitSpeechRecognition' in window)) {
        alert('Speech recognition is not supported in this browser.');
        return;
    }

    recognition = new webkitSpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

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
