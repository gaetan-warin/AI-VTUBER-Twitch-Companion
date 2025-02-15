import { showNotification } from './ui.js';

async function tryGetUserMedia(sourceId, constraints, isDisplayCapture = false) {
    try {
        return await navigator.mediaDevices.getUserMedia({
            audio: false,
            video: {
                mandatory: {
                    chromeMediaSource: 'desktop',
                    chromeMediaSourceId: sourceId,
                    ...constraints
                },
                // Add optional constraints for better compatibility
                optional: [
                    { googTemporalLayeredScreencast: true },
                    { googDisplaySurface: isDisplayCapture ? 'monitor' : 'window' }
                ]
            }
        });
    } catch (error) {
        console.warn(`getUserMedia failed with ${isDisplayCapture ? 'display' : 'window'} capture:`, error);
        return null;
    }
}

async function getStreamWithFallback(sourceId, sourceName) {
    // First try window capture with different constraints
    for (const constraints of [
        { maxWidth: 1920, maxHeight: 1080 },
        { maxWidth: 1280, maxHeight: 720 },
        {}  // No constraints as last resort
    ]) {
        const stream = await tryGetUserMedia(sourceId, constraints);
        if (stream) return stream;
    }

    // If window capture fails, try to find and use the full display capture
    try {
        const sources = await window.electron.getScreenSources();
        const displaySource = sources.find(s =>
            s.name.includes('Screen') ||
            s.name.includes('Display') ||
            s.name.includes('Monitor')
        );

        if (displaySource) {
            showNotification('warning',
                `Window capture failed for "${sourceName}". Falling back to full screen capture. ` +
                'This might be due to hardware acceleration or protected content.'
            );

            return await tryGetUserMedia(displaySource.id, {}, true);
        }
    } catch (error) {
        console.error('Failed to get display sources:', error);
    }

    throw new Error('Failed to capture screen with all available methods');
}

export async function startScreenStream() {
    try {
        const sources = await window.electron.getScreenSources();
        const processedSources = sources.map(source => ({
            id: source.id,
            name: source.name,
            thumbnailDataUrl: source.thumbnail
        }));

        const sourceId = await selectSource(processedSources);
        if (!sourceId) {
            throw new Error('No source selected');
        }

        const stream = await getStreamWithFallback(sourceId, processedSources.find(s => s.id === sourceId).name);
        if (!stream) {
            throw new Error('Failed to capture screen with all available methods');
        }

        return stream;
    } catch (error) {
        console.error('Error starting screen stream:', error);
        handleScreenCaptureError(error);
        throw error;
    }
}

function handleScreenCaptureError(error) {
    let errorMessage = 'Failed to capture screen. ';
    if (error.name === 'NotAllowedError' || error.name === 'PermissionDeniedError') {
        errorMessage += 'Permission denied. Please check your system settings and ensure screen sharing is allowed.';
    } else if (error.name === 'NotReadableError' || error.message.includes('Source is not capturable')) {
        errorMessage += `This window cannot be captured. This is usually due to:
            1. Hardware acceleration (try disabling it in the application)
            2. Protected content (DRM)
            3. System security settings

            Suggestions:
            - Try capturing the entire screen instead
            - Disable hardware acceleration in the target application
            - For browsers, add --disable-gpu to launch options`;
    } else {
        errorMessage += 'An unexpected error occurred. Please try again or select a different source.';
    }
    showNotification('error', errorMessage);
}

export function stopScreenStream(stream) {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
}

function isTrackValid(track) {
    return track &&
        track.readyState === 'live' &&
        track.enabled &&
        !track.muted &&
        track.getSettings().width > 0;  // Additional check for valid dimensions
}

async function ensureValidTrack(stream) {
    if (!stream) return null;

    const videoTrack = stream.getVideoTracks()[0];
    if (!videoTrack) return null;

    // Try to recover track if it's not valid
    if (!isTrackValid(videoTrack)) {
        try {
            // Attempt to restart the track
            await videoTrack.applyConstraints(videoTrack.getConstraints());
            // Wait a moment for the track to stabilize
            await new Promise(resolve => setTimeout(resolve, 100));
        } catch (error) {
            console.warn('Failed to recover video track:', error);
            return null;
        }
    }

    return videoTrack;
}

async function attemptFrameCapture(imageCapture, retries = 3) {
    for (let i = 0; i < retries; i++) {
        try {
            // Wait for a short period before trying
            await new Promise(resolve => setTimeout(resolve, 100));

            const bitmap = await imageCapture.grabFrame();
            return bitmap;
        } catch (error) {
            if (i === retries - 1) throw error;
            console.warn(`Frame capture attempt ${i + 1} failed, retrying...`);
        }
    }
}

async function captureFrameWithVideoElement(stream) {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        video.srcObject = stream;
        video.style.position = 'fixed';
        video.style.opacity = '0';
        document.body.appendChild(video);

        video.onloadedmetadata = () => {
            video.play();
            video.requestVideoFrameCallback(() => {
                try {
                    const canvas = document.createElement('canvas');
                    canvas.width = video.videoWidth;
                    canvas.height = video.videoHeight;
                    const ctx = canvas.getContext('2d');
                    ctx.drawImage(video, 0, 0);
                    const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

                    // Cleanup
                    video.pause();
                    video.srcObject = null;
                    video.remove();
                    canvas.width = 0;
                    canvas.height = 0;

                    resolve(dataUrl);
                } catch (error) {
                    reject(error);
                }
            });
        };

        video.onerror = () => {
            video.remove();
            reject(new Error('Video element failed to load'));
        };
    });
}

export async function captureLastFrameFromStream(stream) {
    if (!stream) {
        console.warn('No stream provided to captureLastFrameFromStream');
        return null;
    }

    try {
        // Ensure valid track
        const videoTrack = await ensureValidTrack(stream);
        if (!videoTrack) {
            console.warn('Could not ensure valid video track');
            // Try fallback method
            return await captureFrameWithVideoElement(stream);
        }

        const imageCapture = new ImageCapture(videoTrack);

        // Add a timeout to prevent hanging
        const timeoutPromise = new Promise((_, reject) => {
            setTimeout(() => reject(new Error('Frame capture timeout')), 5000);
        });

        const bitmap = await Promise.race([
            attemptFrameCapture(imageCapture),
            timeoutPromise
        ]);

        if (!bitmap) {
            // If primary method fails, try fallback
            return await captureFrameWithVideoElement(stream);
        }

        // Convert to canvas and then to base64
        const canvas = document.createElement('canvas');
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(bitmap, 0, 0);

        const dataUrl = canvas.toDataURL('image/jpeg', 0.8);

        // Cleanup
        canvas.width = 0;
        canvas.height = 0;
        return dataUrl;
    } catch (error) {
        console.error('Error capturing frame:', error);
        // Try fallback method if primary method fails
        try {
            return await captureFrameWithVideoElement(stream);
        } catch (fallbackError) {
            console.error('Fallback capture also failed:', fallbackError);
            return null;
        }
    }
}

async function isSourceCapturable(sourceId) {
    try {
        const stream = await tryGetUserMedia(sourceId, {});
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            return true;
        }

        // If window capture fails, check if it's a display source
        const sources = await window.electron.getScreenSources();
        const source = sources.find(s => s.id === sourceId);
        return source && (
            source.name.includes('Screen') ||
            source.name.includes('Display') ||
            source.name.includes('Monitor')
        );
    } catch (error) {
        console.warn(`Source ${sourceId} is not capturable:`, error);
        return false;
    }
}

// Modify the selectSource function to check capturability
function selectSource(sources) {
    return new Promise((resolve) => {
        const dialog = document.createElement('div');
        dialog.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            z-index: 10000;
        `;
        dialog.innerHTML = `
            <h3>Select Screen to Share</h3>
            <div id="sources" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px;"></div>
        `;

        // Add sources as clickable options
        const sourcesContainer = dialog.querySelector('#sources');
        sources.forEach(async (source) => {
            const sourceElement = document.createElement('div');
            sourceElement.style.cssText = `
                cursor: pointer;
                padding: 10px;
                border: 1px solid #ccc;
                border-radius: 4px;
                text-align: center;
                opacity: ${await isSourceCapturable(source.id) ? '1' : '0.5'};
            `;
            // Use the placeholder icon
            sourceElement.innerHTML = `
                <img src="static/images/screen-icon.png" style="width: 64px; height: 64px;"><br>
                ${source.name}
            `;
            sourceElement.onclick = async () => {
                if (await isSourceCapturable(source.id)) {
                    dialog.remove();
                    resolve(source.id);
                } else {
                    showNotification('warning', 'This source may not be capturable. Please try another.');
                }
            };
            sourcesContainer.appendChild(sourceElement);
        });

        // Add cancel button
        const cancelBtn = document.createElement('button');
        cancelBtn.textContent = 'Cancel';
        cancelBtn.style.cssText = `
            margin-top: 10px;
            padding: 8px 16px;
            background: #f44336;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        `;
        cancelBtn.onclick = () => {
            dialog.remove();
            resolve(null);
        };
        dialog.appendChild(cancelBtn);

        document.body.appendChild(dialog);
    });
}
