import { franc } from 'https://cdn.jsdelivr.net/npm/franc@6.1.0/+esm';

const languageMap = {
    'eng': 'en',
    'fra': 'fr',
    'spa': 'es',
    'deu': 'de',
    'ita': 'it',
    'jpn': 'ja',
    'kor': 'ko',
    'cmn': 'zh',
    'rus': 'ru',
    'por': 'pt',
    'nld': 'nl',
    'vie': 'vi',
    'tha': 'th',
    'ara': 'ar',
    'hin': 'hi',
    // Add more mappings as needed
};

export function detectLanguage(text) {
    if (!text || text.length < 10) {
        return 'en'; // Default to English for very short texts
    }

    try {
        const detectedLang = franc(text, {minLength: 3});
        return languageMap[detectedLang] || 'en';
    } catch (error) {
        console.error('Language detection error:', error);
        return 'en';
    }
}

export function isLanguageSupported(langCode) {
    return Object.keys(languageMap).includes(langCode);
}
