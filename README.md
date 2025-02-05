# AI Chat Twitch Bot with Live2D Avatar

This project implements an AI chatbot that interacts with Twitch chat using a Live2D avatar to animate and speak in response to user input. The system leverages WebSockets for real-time communication between the frontend (browser) and backend (Flask server), integrates speech synthesis for the avatar's dialogue, and uses Ollama for local LLM-powered responses.

## Features

- **Live2D Avatar**: A 3D model that moves and speaks in response to chat messages
- **Voice Input**: Speak directly to the avatar using your microphone with speech-to-text conversion
- **Wake Word Detection**: Voice activation using customizable wake words (e.g., "Hey Sarah")
- **Audio Visualization**: Real-time waveform display during voice recording
- **Twitch Integration**: The bot responds to messages in a Twitch channel in real time
- **Local LLM Integration**: Uses Ollama for generating AI responses locally
- **Speech Synthesis**: The avatar speaks responses using text-to-speech (TTS) technology
- **WebSocket Communication**: Real-time interaction between the frontend and backend
- **Avatar Animation**: The mouth of the avatar animates in sync with the speech using sine wave patterns
- **Speech Bubbles**: Configurable speech bubbles to display spoken text
- **Multi-language Support**: Supports multiple languages for both input and output
- **Celebration Effects**: Custom effects for new followers and subscribers
- **UI Configuration**: User-friendly interface for all settings
- **Spam Protection**: Built-in protection against message spam and duplicate messages
- **Input Sanitization**: User input is sanitized to prevent injection attacks

## Requirements

- **Python 3.11.9**
- **Flask**: Web framework for serving the application
- **Flask-SocketIO**: To enable WebSocket communication between the client and the server
- **eventlet**: Required for asynchronous communication with SocketIO
- **Live2D Model Files**: A 3D model used for the avatar animations
- **Twitch API Token**: To connect to Twitch chat and listen for user messages
- **Ollama**: Local LLM server for generating responses
- **bleach**: Library for sanitizing user input
- **Web Browser**: Modern browser with WebSpeech API support for voice input/output

## Setup

1. **Clone the repository**:
    ```bash
    git clone https://github.com/gaetan-warin/AI-VTUBER-Twitch-Companion.git
    cd AI-VTUBER-Twitch-Companion
    ```

2. **Install dependencies**:
    Ensure you have Python 3.11.9 and `pip` installed. Then install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure your `.env` file**:
    Create a `.env` file in the root directory and add your configuration:
    ```env
    # Avatar Server
    PRE_PROMPT="Respond in less than 150 characters and be as consistent as possible."
    API_URL=http://127.0.0.1
    API_URL_PORT=5000
    OLLAMA_MODEL=deepseek-r1:1.5b

    # Twitch
    TWITCH_TOKEN=YOUR_TWITCH_TOKEN
    CLIENT_ID=YOUR_TWITCH_CLIENT_ID
    BOT_NAME=ai_chat_bot
    CHANNEL_NAME=YOUR_CHANNEL_NAME
    EXTRA_DELAY_LISTENER=3
    NB_SPAM_MESSAGE=3
    ```

4. **Model Files**:
    (Optional) : if you want to change model file:
    - Place the model folder under the `model/` directory
    - Ensure all necessary textures, expressions, and motion files are available within their respective subdirectories
    
    /!\ This repo work with .moc (Live2D Cubism 2.0) model
    Info: [Live2d](https://www.live2d.com/en/)

5. **Start Ollama**:
    - Install Ollama from [ollama.ai](https://ollama.ai)
    - Pull the deepseek-r1:1.5b model or your preferred model
    - Start the Ollama server

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
- `PERSONA_NAME`: Name of the AI assistant
- `PERSONA_ROLE`: Role description for the AI
- `FIXED_LANGUAGE`: Default language for speech (e.g., 'en', 'fr')
- `VOICE_GENDER`: Preferred voice gender ('male' or 'female')
- `BACKGROUND_IMAGE`: Default background image
- `WAKE_WORD`: Word to trigger voice activation
- `WAKE_WORD_ENABLED`: Enable/disable wake word detection
- `SPEECH_BUBBLE_ENABLED`: Enable/disable speech bubbles
- `TWITCH_TOKEN`: Your Twitch OAuth token
- `CLIENT_ID`: Your Twitch application client ID
- `CHANNEL_NAME`: The Twitch channel to monitor
- `BOT_NAME_FOLLOW_SUB`: Bot name for follow/sub notifications
- `CELEBRATE_FOLLOW`: Enable/disable follow celebrations
- `CELEBRATE_SUB`: Enable/disable subscription celebrations
- `CELEBRATE_SOUND`: Sound effect for celebrations

## How It Works

1. **Multiple Input Methods**:
   - **Voice Input**: Speak directly to the avatar using your microphone
   - **Text Input**: Type messages in the interface
   - **Twitch Chat**: Messages from Twitch chat with `!ai` prefix
2. **Voice Processing**:
   - Wake word detection to activate voice input
   - Speech-to-text conversion using browser's WebSpeech API
   - Visual feedback with audio waveform display
3. **Spam Protection**: Messages are checked for spam and duplicate content
4. **LLM Processing**: Valid messages are processed by Ollama to generate contextual responses
5. **WebSocket Communication**: Responses are sent via WebSocket to the frontend
6. **Speech Synthesis**: The frontend converts the text to speech using the browser's `speechSynthesis` API
7. **Avatar Animation**: The avatar's mouth moves in sync with the speech using GSAP animations

## Architecture

- **Frontend**: HTML5, JavaScript with WebSocket support, Live2D SDK, WebSpeech API
- **Backend**: Flask server with SocketIO for real-time communication
- **AI**: Local LLM using Ollama for generating responses
- **Twitch Integration**: TwitchIO for chat interaction
- **Animation**: GSAP for smooth mouth movements

## Features Configuration

### Voice Input Settings
- Enable/disable wake word detection
- Customize wake word (default: "Hey Sarah")
- Toggle audio waveform visualization
- Microphone selection through browser settings

## Contributing

Feel free to fork the repository, submit issues, and create pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: You must have the Live2D model files and related resources to use the avatar animation functionality. One is included in this repo as an example.
