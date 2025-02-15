const puppeteer = require("puppeteer");
const express = require("express");
const http = require("http");
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app);

// Configure CORS properly
const io = new Server(server, {
    cors: {
        origin: ["http://localhost:5000", "http://127.0.0.1:5000"],
        methods: ["GET", "POST"],
        credentials: true,
        allowedHeaders: ["*"]
    },
    transports: ['websocket', 'polling']
});

// Add basic health check endpoint
app.get('/health', (req, res) => {
    res.status(200).json({ status: 'healthy' });
});

(async () => {
    try {
        const browser = await puppeteer.launch({
            headless: "new",
            args: [
                "--use-fake-ui-for-media-stream",
                "--disable-web-security",
                "--allow-running-insecure-content"
            ]
        });
        const page = await browser.newPage();

        await page.evaluate(() => {
            window.startRecognition = (lang) => {
                console.log('Starting recognition in language:', lang);
                const recognition = new webkitSpeechRecognition();
                recognition.continuous = true;
                recognition.interimResults = true;
                recognition.lang = lang || "en-US";

                recognition.onstart = () => {
                    console.log('Speech recognition started');
                };

                recognition.onresult = (event) => {
                    let transcript = "";
                    let isFinal = false;

                    for (let i = event.resultIndex; i < event.results.length; i++) {
                        transcript += event.results[i][0].transcript + " ";
                        isFinal = event.results[i].isFinal;
                    }

                    const trimmedTranscript = transcript.trim();
                    console.log(`Speech ${isFinal ? 'final' : 'interim'}: "${trimmedTranscript}"`);

                    if (isFinal) {
                        console.log('Sending final transcript to client:', trimmedTranscript);
                        // Use postMessage instead of socket.emit
                        window.postMessage({
                            type: 'speechData',
                            data: trimmedTranscript
                        }, '*');
                    }
                };

                recognition.onerror = (event) => {
                    console.error("Speech recognition error:", event.error);
                };

                recognition.onend = () => {
                    console.log('Speech recognition ended');
                };

                recognition.start();
            };
        });

        // Listen for page messages and relay to socket.io
        page.on('console', msg => console.log('Page log:', msg.text()));

        // Add message listener to handle speech data
        await page.exposeFunction('relayToSocket', (data) => {
            console.log('Relaying to socket:', data);
            io.emit('speechData', data);
        });

        // Set up message handler in page context
        await page.evaluate(() => {
            window.addEventListener('message', event => {
                if (event.data.type === 'speechData') {
                    window.relayToSocket(event.data.data);
                }
            });
        });

        io.on("connection", (socket) => {
            console.log("Client connected to speech server");

            socket.on("startSpeech", async (data) => {
                try {
                    const lang = data?.lang || "en-US";
                    console.log('Starting speech recognition with language:', lang);
                    await page.evaluate((lang) => window.startRecognition(lang), lang);
                } catch (error) {
                    console.error('Error starting speech recognition:', error);
                    socket.emit('error', { message: 'Failed to start speech recognition' });
                }
            });

            socket.on('disconnect', () => {
                console.log('Client disconnected from speech server');
            });
        });

        // Listen for speech data from page context
        page.on('domcontentloaded', () => {
            page.exposeFunction('emitSpeechData', (data) => {
                io.emit('speechData', data);
            });
        });

        server.listen(3000, '0.0.0.0', () => {
            console.log("Speech server running on port 3000");
            require('fs').writeFileSync('speech-server-status.json',
                JSON.stringify({ status: 'running', pid: process.pid }));
        });

    } catch (error) {
        console.error("Speech server failed to start:", error);
        process.exit(1);
    }
})();

// Clean up on exit
process.on('exit', () => {
    try {
        require('fs').unlinkSync('speech-server-status.json');
    } catch (e) {
        // Ignore cleanup errors
    }
});

// Handle process termination
process.on('SIGINT', () => process.exit(0));
process.on('SIGTERM', () => process.exit(0));
