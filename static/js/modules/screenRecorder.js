export async function startScreenStream(captureOption = 'default') {
    // Build constraints; optionally add displaySurface hint if provided.
    const constraints = { video: { cursor: "always" } };
    if (captureOption !== 'default') {
        constraints.video.displaySurface = captureOption; // e.g. "monitor", "window", "application"
    }
    // Start the screen capture stream
    return await navigator.mediaDevices.getDisplayMedia(constraints);
}

export async function captureLastFrameFromStream(stream) {
    return new Promise((resolve, reject) => {
        const video = document.createElement('video');
        video.srcObject = stream;
        video.play().then(() => {
            // Wait a moment for the video frame to update
            setTimeout(() => {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                resolve(canvas.toDataURL('image/png'));
            }, 200);
        }).catch(reject);
    });
}

export function stopScreenStream(stream) {
    if (stream) {
        stream.getTracks().forEach(track => track.stop());
    }
}

export async function startScreenRecording() {
    // Request screen capture stream
    const stream = await startScreenStream();
    let recordedChunks = [];
    const mediaRecorder = new MediaRecorder(stream);

    mediaRecorder.ondataavailable = event => {
        if (event.data.size > 0) {
            recordedChunks.push(event.data);
        }
    };

    mediaRecorder.onstop = () => {
        const blob = new Blob(recordedChunks, { type: 'video/webm' });
        // Process or download the recorded video blob as needed
        console.log('Recording stopped. Blob size:', blob.size);
    };

    // Start recording
    mediaRecorder.start();
    console.log('Screen recording started.');

    return { mediaRecorder, stream };
}
