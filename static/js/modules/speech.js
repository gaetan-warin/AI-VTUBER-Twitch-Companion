export const synth = window.speechSynthesis;
export const mouthState = { value: 0 };
let isSpeaking = false;
let voicesReady = false;
let currentLanguage = 'en';
const languageVoiceMap = {};

// Add preferred voice mapping
const preferredVoices = {
    'en': {
        female: 'Google UK English Female',      // Primary choice for English female
        male: 'Google UK English Male'        // Primary choice for English male
    },
    'fr': {
        female: 'Google français',
        male: 'Microsoft Paul - French (France)'
    }
};

export function initializeSpeech() {
    return new Promise((resolve) => {
        const checkVoices = () => {
            const voices = synth.getVoices();
            if (voices.length > 0) {
                voicesReady = true;
                mapVoicesToLanguages(voices);
                resolve();
            } else {
                setTimeout(checkVoices, 100);
            }
        };

        if (synth.onvoiceschanged !== undefined) {
            synth.onvoiceschanged = checkVoices;
        }

        checkVoices();
    });
}

function mapVoicesToLanguages(voices) {
    voices.forEach(voice => {
        const langCode = voice.lang.split('-')[0];
        if (!languageVoiceMap[langCode]) {
            languageVoiceMap[langCode] = [];
        }
        languageVoiceMap[langCode].push(voice);
    });
    console.log('Language-Voice mapping:', languageVoiceMap);
}

function getBestVoiceForLanguage(langCode) {
    const voices = languageVoiceMap[langCode] || languageVoiceMap['en'];
    const preferredGender = $('#voiceGender').val() || 'female';
    
    // Try to find the preferred voice for the selected gender
    if (preferredVoices[langCode]) {
        const preferredName = preferredVoices[langCode][preferredGender];
        const preferredVoice = voices.find(v => v.name.includes(preferredName));
        if (preferredVoice) return preferredVoice;
    }

    // If preferred voice not found, try any voice with the selected gender
    const genderVoice = voices.find(v => 
        v.name.toLowerCase().includes(preferredGender)
    );
    if (genderVoice) return genderVoice;

    // Finally, return the first available voice
    return voices[0];
}

export function areVoicesReady() {
    return voicesReady;
}

export function speak(text, language = null) {
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

    // Use provided language from backend or fallback to default
    currentLanguage = language || 'en';
    console.log('Using language:', currentLanguage);

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
                const voice = getBestVoiceForLanguage(currentLanguage);

                Object.assign(utterance, {
                    voice: voice,
                    pitch: 1.1,
                    rate: 0.95,
                    lang: voice.lang,
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

export function animateMouth() {
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

export function stopMouthAnimation() {
    gsap.killTweensOf(mouthState);
    gsap.to(mouthState, {
        duration: 0.3,
        value: 0,
        ease: "power2.out"
    });
}

function showSpeechBubble(text) {
    if ($('#speechBubbleEnabled').is(':checked')) {
        const bubble = $('#speech-bubble');
        bubble.text(text).show();
    }
}

function hideSpeechBubble() {
    $('#speech-bubble').hide();
}

export function isSpeakingNow() {
    return isSpeaking;
}

export function getCurrentLanguage() {
    return currentLanguage;
}
