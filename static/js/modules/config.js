import { emit } from './socket.js';

export const config = {
    fields: [
        'AVATAR_MODEL', 'PERSONA_NAME', 'PERSONA_ROLE', 'PRE_PROMPT', 'BACKGROUND_IMAGE',
        'CHANNEL_NAME', 'TWITCH_TOKEN', 'CLIENT_ID', 'EXTRA_DELAY_LISTENER', 'NB_SPAM_MESSAGE',
        'OLLAMA_MODEL', 'BOT_NAME_FOLLOW_SUB', 'KEY_WORD_FOLLOW', 'KEY_WORD_SUB',
        'DELIMITER_NAME', 'DELIMITER_NAME_END', 'FIXED_LANGUAGE', 'VOICE_GENDER'
    ],
    get() {
        return this.fields.reduce((acc, field) => {
            const $element = $(`#${this.snakeToCamelCase(field)}`);
            if ($element.length) {
                const value = $element.val();
                if (value !== undefined && value !== null) {
                    acc[field] = value.trim();
                }
            }
            return acc;
        }, {});
    },
    set(data) {
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
    snakeToCamelCase(str) {
        return str.toLowerCase().replace(/([-_][a-z])/g, group =>
            group.toUpperCase().replace('-', '').replace('_', '')
        );
    },
    camelToSnakeCase(str) {
        return str.replace(/[A-Z]/g, letter => `_${letter.toLowerCase()}`);
    }
};

export function populateSelectElement(selector, items) {
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

export function saveConfig() {
    const configData = config.get();
    console.log("save config:", configData);
    emit('save_config', configData);
}

export function saveModalConfig() {
    $('#configModal').hide();
    saveConfig();
}
