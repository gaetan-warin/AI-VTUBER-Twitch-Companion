# AI Chat Twitch Bot with Live2D Avatar

This project implements a simple AI chatbot that interacts with Twitch chat, using a Live2D avatar to animate and speak in response to user input. The system leverages WebSockets to facilitate communication between the frontend (browser) and backend (Flask server) and integrates speech synthesis for the avatar's dialogue.

## Features

- **Live2D Avatar**: A 3D model that moves and speaks in response to chat messages.
- **Twitch Integration**: The bot responds to messages in a Twitch channel in real time.
- **Speech Synthesis**: The avatar speaks text entered by the Twitch chat using text-to-speech (TTS) technology.
- **WebSocket Communication**: Real-time interaction between the frontend and backend.
- **Avatar Animation**: The mouth of the avatar animates in sync with the speech using sine wave patterns.

## Requirements

- **Python 3.11.9**
- **Flask**: Web framework for serving the application.
- **Flask-SocketIO**: To enable WebSocket communication between the client and the server.
- **eventlet**: Required for asynchronous communication with SocketIO.
- **Live2D Model Files**: A 3D model used for the avatar animations.
- **Twitch API Token**: To connect to Twitch chat and listen for user messages.

## Setup

1. **Clone the repository**:
    ```bash
    git clone https://github.com/gaetan-warin/SMART-AI-VTUBER.git
    cd ai-chat-bot
    ```

2. **Install dependencies**:
    Ensure you have Python 3.11.9 and `pip` installed. Then install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. **Configure your `.env` file**:
    Create a `.env` file in the root directory and add your Twitch credentials and other settings:
    ```env
    TOKEN=YOUR_TWITCH_TOKEN
    CLIENT_ID=YOUR_TWITCH_CLIENT_ID
    CHANNEL_NAME=YOUR_CHANNEL_NAME
    PRE_PROMPT="Respond in less than 150 characters and be as consistent as possible."
    API_URL=http://localhost:5000/
    ```

4. **Model Files**:
    - The model files (e.g., `shizuku.model.json`) should be placed under the `model/shizuku` directory.
    - Make sure all necessary textures, expressions, and motion files are available within their respective subdirectories.

5. **Run the Application**:
    Start the Flask server with WebSocket support:
    ```bash
    python app.py
    ```

6. Open your browser and visit [http://localhost:5000](http://localhost:5000) to see the avatar.

## Frontend Overview

- **HTML**: Contains a text input field and a button to trigger the avatar to speak.
- **JS**: Utilizes the `speechSynthesis` API for speech generation and synchronizes the Live2D model's mouth movements with speech.
- **WebSocket**: Handles communication with the Flask backend to receive and emit speech data.

## Backend Overview

- **Flask Server**: The backend is built using Flask, which serves the web page, model files, and other static resources.
- **SocketIO**: Used to handle real-time communication for sending and receiving the speech text to be spoken by the avatar.
- **Twitch Integration**: The bot listens for chat messages in a specified Twitch channel and responds using speech synthesis.

## How It Works

1. **User Input via Twitch**: The bot listens for messages in the specified Twitch channel.
2. **WebSocket Communication**: The message is sent via WebSocket to the backend server.
3. **Speech Synthesis**: The backend sends the text to the frontend, where it’s spoken using the browser's `speechSynthesis` API.
4. **Avatar Animation**: The avatar's mouth opens and closes to simulate speech using GSAP (GreenSock Animation Platform).

## Endpoints

- `GET /`: Renders the main web page with the avatar and chat interface.
- `POST /trigger_speak`: Triggers speech synthesis on the backend by sending a JSON object containing the text to speak.
- `GET /static/<path:filename>`: Serves static files such as JavaScript, CSS, and images.
- `GET /model/shizuku/<path:filename>`: Serves model-related files like textures and motion data.

## Example Usage

- The bot will listen for chat messages in the configured Twitch channel.
- It will animate the Live2D avatar and speak the message text using TTS.
- You can interact with the bot by sending text via Twitch chat.

## Contribution

Feel free to fork the repository, submit issues, and create pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: You must have the Live2D model files and related resources to use the avatar animation functionality.
