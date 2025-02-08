import { mouthState, isSpeakingNow } from './speech.js';

let currentModel = null;
let modelPath = '';

export function initializeModel() {
    // This function can be used for any initial setup related to the model
    console.log('Model module initialized');
}

export async function loadModel(app, modelPath) {
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

        setupMouthMovement(model, modelPath);
        return model;
    } catch (error) {
        console.error('Model loading error:', error);
    }
}

export function loadAvatarModel(modelPath) {
    if (!modelPath) {
        console.error('Model path not set.');
        return;
    }

    if (currentModel) {
        currentModel.destroy();
        currentModel = null;
    }

    const app = new PIXI.Application({
        view: document.getElementById('canvas'),
        autoStart: true,
        resizeTo: window,
        transparent: true,
        antialias: true
    });

    app.ticker.add(() => {
        if (currentModel && mouthState.value !== undefined) {
            updateMouthState(mouthState.value);
        }
    });

    loadModel(app, modelPath);
}

function setupMouthMovement(model, modelPath) {
    model.internalModel.motionManager.update = () => {
        if (modelPath.includes("model.json")) {
            model.internalModel.coreModel.setParamFloat('PARAM_MOUTH_OPEN_Y', mouthState.value);
        } else {
            const parameterIndex = model.internalModel.coreModel.getParameterIndex("ParamMouthOpenY");
            model.internalModel.coreModel.setParameterValueByIndex(parameterIndex, mouthState.value);
        }
    };
}

function updateMouthState(value) {
    if (isSpeakingNow())
        mouthState.value = value;
}

export function getModelPath(selectedModel) {
    switch (selectedModel) {
        case 'haru':
            return `models/${selectedModel}/haru_greeter_t03.model3.json`;
        case 'mark':
            return `models/${selectedModel}/mark_free_t04.model3.json`;
        case 'miku':
            return `models/${selectedModel}/miku.model3.json`;
        case 'hibiki':
            return `models/${selectedModel}/hibiki.model3.json`;
        case 'Epsilon':
            return `models/${selectedModel}/Epsilon_free.model3.json`;
        default:
            return `models/${selectedModel}/${selectedModel}.model.json`;
    }
}
