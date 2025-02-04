let celebrationAudio;

export function initializeEffects() {
    celebrationAudio = new Audio('static/mp3/success.mp3');
    celebrationAudio.volume = 0.3;
    celebrationAudio.preload = 'auto';
}

export function triggerFireworks() {
    celebrationAudio.currentTime = 0;
    celebrationAudio.play().catch(error => console.log("Audio playback failed:", error));

    const duration = 5 * 1000;
    const animationEnd = Date.now() + duration;
    const defaults = { startVelocity: 30, spread: 360, ticks: 60, zIndex: 0 };

    const interval = setInterval(() => {
        const timeLeft = animationEnd - Date.now();
        if (timeLeft <= 0) return clearInterval(interval);
        const particleCount = 50 * (timeLeft / duration);
        confetti({ ...defaults, particleCount, origin: { x: Math.random(), y: Math.random() - 0.2 } });
    }, 250);

    confetti({
        particleCount: 100,
        spread: 70,
        origin: { y: 0.6 },
        colors: ['#ff0000', '#00ff00', '#0000ff']
    });
}
