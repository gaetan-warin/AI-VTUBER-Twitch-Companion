# AI Chat Twitch Bot with Live2D Avatar

![Chat Bot Image](https://mywebsuccess.be/wp-content/uploads/2025/02/2025-02-08-23_48_06-NVIDIA-GeForce-Overlay.png)

This project implements an AI chatbot that interacts with Twitch chat using a Live2D avatar to animate and speak in response to user input. The system leverages WebSockets for real-time communication between the frontend (browser) and backend (Flask server), integrates speech synthesis for the avatar's dialogue, and supports multiple AI providers including Ollama (local) and Google Gemini (cloud).

## Features

- **Live2D Avatar**: A 3D model that moves and speaks in response to chat messages
- **Dual AI Provider Support**: Choose between Ollama (local) or Google Gemini (cloud-based)
- **Vision Capabilities**: Screen sharing and image analysis with Gemini vision models
- **Voice Input**: Speak directly to the avatar using your microphone with speech-to-text conversion
- **Wake Word Detection**: Voice activation using customizable wake words (e.g., "Hey Sarah")
- **Audio Visualization**: Real-time waveform display during voice recording
- **Twitch Integration**: The bot responds to messages in a Twitch channel in real time
- **Text-to-Speech Optimized**: Responses cleaned for natural TTS playback (no emojis, special characters, etc.)
- **Speech Synthesis**: The avatar speaks responses using text-to-speech (TTS) technology
- **WebSocket Communication**: Real-time interaction between the frontend and backend
- **Avatar Animation**: The mouth of the avatar animates in sync with the speech using sine wave patterns
- **Speech Bubbles**: Configurable speech bubbles to display spoken text
- **Multi-language Support**: Supports multiple languages for both input and output
- **Celebration Effects**: Custom effects for new followers and subscribers
- **RAG System**: Document-based knowledge retrieval for context-aware responses
- **File Manager**: Upload and manage documents for the RAG system
- **Rate Limiting**: Built-in protection against API rate limits
- **Error Notifications**: Beautiful frontend error notifications for user feedback
- **UI Configuration**: User-friendly interface for all settings
- **Spam Protection**: Built-in protection against message spam and duplicate messages
- **Input Sanitization**: User input is sanitized to prevent injection attacks
- **Background Image Selection**: Choose from available background images in the UI

## Requirements

- **Python 3.13+** (tested with 3.13.9)
- **Flask**: Web framework for serving the application
- **Flask-SocketIO**: To enable WebSocket communication between the client and the server
- **eventlet**: Required for asynchronous communication with SocketIO
- **Google Generative AI**: For Gemini API integration (optional)
- **Pillow**: For image processing with vision features
- **Live2D Model Files**: A 3D model used for the avatar animations
- **Twitch API Token**: To connect to Twitch chat and listen for user messages
- **Ollama** (optional): Local LLM server for generating responses
- **Gemini API Key** (optional): For cloud-based AI with vision capabilities
- **bleach**: Library for sanitizing user input
- **Web Browser**: Modern browser with WebSpeech API support for voice input/output

## Setup

1. **Clone the repository**:
    ```bash
    git clone https://github.com/gaetan-warin/AI-VTUBER-Twitch-Companion.git
    cd AI-VTUBER-Twitch-Companion
    ```

2. **Install dependencies**:
    Ensure you have Python 3.13+ and `pip` installed. Then install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure your `.env` file**:
    Create a `.env` file in the root directory and add your configuration:
    ```env
    # Avatar & Persona Settings
    PERSONA_NAME=Sarah
    PERSONA_ROLE=Virtual assistant providing calm and engaging interactions
    PRE_PROMPT=Please respond concisely and avoid monologues.
    AVATAR_MODEL=shizuku
    BACKGROUND_IMAGE=classroom.jpg

    # API Server Settings
    API_URL=http://127.0.0.1
    API_URL_PORT=5000
    SOCKETIO_IP=127.0.0.1
    SOCKETIO_IP_PORT=5000
    SOCKETIO_CORS_ALLOWED=*

    # AI Provider Settings (choose one)
    AI_PROVIDER=gemini
    # For Ollama (local)
    OLLAMA_MODEL=deepseek-r1:1.5b
    # For Gemini (cloud)
    GEMINI_API_KEY=your_gemini_api_key_here
    GEMINI_MODEL=gemini-2.0-flash-lite

    # Twitch Settings
    TWITCH_TOKEN=YOUR_TWITCH_TOKEN
    TWITCH_CLIENT_ID=YOUR_TWITCH_CLIENT_ID
    CHANNEL_NAME=YOUR_CHANNEL_NAME
    BOT_NAME_FOLLOW_SUB=ai_chat_bot
    EXTRA_DELAY_LISTENER=3
    NB_SPAM_MESSAGE=3

    # Feature Toggles
    WAKE_WORD_ENABLED=True
    WAKE_WORD=Hey Sarah
    SPEECH_BUBBLE_ENABLED=True
    CELEBRATE_FOLLOW=True
    CELEBRATE_SUB=True
    ASK_RAG=False

    # Language & Voice
    FIXED_LANGUAGE=fr
    VOICE_GENDER=female
    ```

4. **Model Files**:
    (Optional) : if you want to change model file:
    - Place the model folder under the `models/` directory
    - Ensure all necessary textures, expressions, and motion files are available within their respective subdirectories

    /!\ This repo works with .moc (Live2D Cubism 2.0) models
    Info: [Live2d](https://www.live2d.com/en/)

5. **Choose Your AI Provider**:
    
    **Option A - Ollama (Local)**:
    - Install Ollama from [ollama.ai](https://ollama.ai)
    - Pull a model: `ollama pull deepseek-r1:1.5b`
    - Start the Ollama server
    - Set `AI_PROVIDER=ollama` in your .env file
    
    **Option B - Google Gemini (Cloud)**:
    - Get an API key from [Google AI Studio](https://aistudio.google.com/app/apikey)
    - Set `AI_PROVIDER=gemini` in your .env file
    - Set your `GEMINI_API_KEY` in the .env file
    - Choose a model: `gemini-2.0-flash-lite`, `gemini-2.0-flash-exp`, `gemini-1.5-flash`, or `gemini-1.5-pro`
    - Note: Free tier has limits (15 requests/min, 1500 requests/day)

6. **Run the Application**:
    Start the Flask server with WebSocket support:
    ```bash
    python app.py
    ```

7. Open your browser and visit [http://localhost:5000](http://localhost:5000) to see the avatar.

## Environment Variables

- `PRE_PROMPT`: System prompt for the LLM to maintain consistent responses
- `SOCKETIO_IP`: IP for socket.io
- `SOCKETIO_IP_PORT`: Port for socket.io
- `API_URL`: IP of flash server
- `API_URL_PORT`: Port of flash server
- `OLLAMA_MODEL`: The Ollama model to use (default: deepseek-r1:1.5b)
- `AVATAR_MODEL`: The Live2D model to use (default: shizuku)
## Environment Variables

### Avatar & Persona
- `PERSONA_NAME`: Name of the AI assistant (default: Sarah)
- `PERSONA_ROLE`: Role description for the AI
- `PRE_PROMPT`: System prompt for the LLM to maintain consistent responses
- `AVATAR_MODEL`: The Live2D model to use (default: shizuku)
- `BACKGROUND_IMAGE`: Default background image

### API Server
- `API_URL`: IP of Flask server (default: http://127.0.0.1)
- `API_URL_PORT`: Port of Flask server (default: 5000)
- `SOCKETIO_IP`: IP for socket.io (default: 127.0.0.1)
- `SOCKETIO_IP_PORT`: Port for socket.io (default: 5000)
- `SOCKETIO_CORS_ALLOWED`: CORS settings (default: *)

### AI Provider Settings
- `AI_PROVIDER`: Choose 'ollama' for local or 'gemini' for cloud (default: ollama)
- `OLLAMA_MODEL`: The Ollama model to use (e.g., deepseek-r1:1.5b, llama3.2)
- `GEMINI_API_KEY`: Your Google Gemini API key (required if using Gemini)
- `GEMINI_MODEL`: Gemini model to use:
  - `gemini-2.0-flash-lite` - Fastest, most cost-effective
  - `gemini-2.0-flash-exp` - Experimental, high performance
  - `gemini-1.5-flash` - Balanced performance
  - `gemini-1.5-pro` - Most capable, slower

### Twitch Integration
- `TWITCH_TOKEN`: Your Twitch OAuth token
- `TWITCH_CLIENT_ID`: Your Twitch application client ID
- `CHANNEL_NAME`: The Twitch channel to monitor
- `BOT_NAME_FOLLOW_SUB`: Bot name for follow/sub notifications
- `EXTRA_DELAY_LISTENER`: Delay between listener checks (seconds)
- `NB_SPAM_MESSAGE`: Number of similar messages to trigger spam protection

### Features & Behavior
- `WAKE_WORD`: Word to trigger voice activation (default: "Hey Sarah")
- `WAKE_WORD_ENABLED`: Enable/disable wake word detection (True/False)
- `SPEECH_BUBBLE_ENABLED`: Enable/disable speech bubbles (True/False)
- `CELEBRATE_FOLLOW`: Enable/disable follow celebrations (True/False)
- `CELEBRATE_SUB`: Enable/disable subscription celebrations (True/False)
- `CELEBRATE_FOLLOW_MESSAGE`: Custom message for new followers
- `CELEBRATE_SUB_MESSAGE`: Custom message for new subscribers
- `CELEBRATE_SOUND`: Sound effect for celebrations
- `ASK_RAG`: Enable/disable RAG document retrieval (True/False)

### Language & Voice
- `FIXED_LANGUAGE`: Default language for speech (e.g., 'en', 'fr', 'es', 'de', 'ja')
- `VOICE_GENDER`: Preferred voice gender ('male' or 'female')

## How It Works

1. **Multiple Input Methods**:
   - **Voice Input**: Speak directly to the avatar using your microphone
   - **Text Input**: Type messages in the interface
   - **Screen Sharing**: Share your screen for visual context (Gemini vision)
   - **Twitch Chat**: Messages from Twitch chat with `!ai` prefix

2. **Voice Processing**:
   - Wake word detection to activate voice input
   - Speech-to-text conversion using browser's WebSpeech API
   - Visual feedback with audio waveform display

3. **Smart Conversation Context**:
   - Maintains conversation history for contextual responses
   - Deduplicates repeated messages
   - Properly alternates between user and assistant messages
   - Reduces history when using vision features to save context

4. **AI Processing**:
   - **Ollama**: Local, private, no rate limits, requires local setup
   - **Gemini**: Cloud-based, includes vision capabilities, has rate limits (15/min free tier)
   - Automatic rate limiting to prevent 429 errors
   - Smart prompt engineering for natural, conversational responses

5. **Text-to-Speech Optimization**:
   - Removes emojis and emoticons
   - Cleans special characters and quotes
   - Removes gender alternatives like "Prêt(e)"
   - Ensures natural pronunciation for TTS engines

6. **WebSocket Communication**: Responses are sent via WebSocket to the frontend

7. **Speech Synthesis**: The frontend converts the text to speech using the browser's `speechSynthesis` API

8. **Avatar Animation**: The avatar's mouth moves in sync with the speech using GSAP animations

9. **Error Handling**: Beautiful error notifications for rate limits and API errors

## Architecture

- **Frontend**: 
  - HTML5, JavaScript with WebSocket support
  - Live2D SDK for avatar rendering
  - WebSpeech API for voice input/output
  - jQuery for DOM manipulation
  - GSAP for smooth animations
  
- **Backend**: 
  - Flask server with SocketIO for real-time communication
  - Dual AI provider support (Ollama/Gemini)
  - RAG system with BM25 for document retrieval
  - Image processing with Pillow for vision features
  - Rate limiting and error handling
  
- **AI Providers**:
  - **Ollama**: Local LLM inference
  - **Gemini**: Cloud-based with vision capabilities
  
- **Twitch Integration**: TwitchIO for chat interaction

- **Animation**: GSAP for smooth mouth movements

## Key Features Explained

### AI Provider Selection
Switch between Ollama (local) and Gemini (cloud) in the settings panel:
- **Ollama**: Best for privacy, unlimited usage, requires local GPU
- **Gemini**: Best for convenience, includes vision, has free tier limits

### Vision Capabilities (Gemini only)
- Click "Start Stream" to share your screen
- Ask questions about what's on screen
- AI can see and analyze code, images, documents
- Automatically reduces conversation history to save context

### RAG System
- Upload documents via File Manager
- AI retrieves relevant context from documents
- Supports PDF and text files
- Toggle with ASK_RAG setting

### Rate Limiting
- Automatic 4-second delay between Gemini requests
- Prevents 429 rate limit errors
- User-friendly error messages when limits are hit

### Conversation Memory
- Maintains last 10 messages for context
- Reduces to 6 messages when using vision
- Deduplicates repeated greetings
- Smart greeting detection to avoid repetitive "Hi"

## Features Configuration

### Voice Input Settings
- Enable/disable wake word detection
- Customize wake word (default: "Hey Sarah")
- Toggle audio waveform visualization
- Microphone selection through browser settings

### AI Settings
- Choose between Ollama and Gemini
- Configure API keys and models
- Enable/disable speech bubbles
- Toggle RAG document retrieval

### Celebration Settings
- Enable/disable follower celebrations
- Enable/disable subscriber celebrations
- Customize celebration messages
- Select celebration sound effects

## Troubleshooting

### Gemini Rate Limits
- Free tier: 15 requests/min, 1500/day
- Wait between requests or upgrade to paid tier
- Consider using Ollama for unlimited local inference

### Ollama Connection Issues
- Ensure Ollama is running: `ollama serve`
- Check model is installed: `ollama list`
- Pull model if needed: `ollama pull deepseek-r1:1.5b`

### TTS Not Working
- Check browser compatibility (Chrome/Edge recommended)
- Ensure volume is not muted
- Try different voice settings in browser

### Vision Not Working
- Only available with Gemini provider
- Ensure screen sharing permissions granted
- Check that Gemini model supports vision (Flash/Pro)

## Contributing

Feel free to fork the repository, submit issues, and create pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: You must have the Live2D model files and related resources to use the avatar animation functionality. One is included in this repo as an example.
