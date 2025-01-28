# AI Chat Bot with Live2D Avatar

This project implements a simple AI chatbot that uses a Live2D avatar to animate and speak in response to user input. The system leverages WebSockets to facilitate communication between the frontend (browser) and backend (Flask server) and integrates speech synthesis for the avatar's dialogue.

## Features

- **Live2D Avatar**: A 3D model that moves in response to speech.
- **Speech Synthesis**: The avatar speaks text entered by the user.
- **WebSocket Communication**: Real-time interaction between the frontend and backend.
- **Avatar Animation**: The mouth of the avatar animates in sync with the speech using sine wave patterns.

## Requirements

- **Python 3.x**
- **Flask**: Web framework for serving the application.
- **Flask-SocketIO**: To enable WebSocket communication between the client and the server.
- **eventlet**: Required for asynchronous communication with SocketIO.
- **Live2D Model Files**: A 3D model (Shizuku) used for the avatar animations.

## Setup

1. **Clone the repository**:
    ```bash
    git clone https://github.com/your-username/ai-chat-bot.git
    cd ai-chat-bot
    ```

2. **Install dependencies**:
    Ensure you have Python 3.x and `pip` installed. Then install the required packages:
    ```bash
    pip install -r requirements.txt
    ```

3. **Model Files**: 
    - The model files (e.g., `shizuku.model.json`) should be placed under the `model/shizuku` directory. 
    - Make sure all necessary textures, expressions, and motion files are available within their respective subdirectories.

4. **Run the Application**:
    Start the Flask server with WebSocket support:
    ```bash
    python app.py
    ```

5. Open your browser and visit [http://localhost:5000](http://localhost:5000).

## Frontend Overview

- **HTML**: Contains a text input field and a button to trigger the avatar to speak.
- **JS**: Utilizes the `speechSynthesis` API for speech generation and synchronizes the Live2D model's mouth movements with speech.
- **WebSocket**: Handles communication with the Flask backend to receive and emit speech data.

## Backend Overview

- **Flask Server**: The backend is built using Flask, which serves the web page, model files, and other static resources.
- **SocketIO**: Used to handle real-time communication for sending and receiving the speech text to be spoken by the avatar.

## How It Works

1. **User Input**: The user types text into the input field and clicks the "Speak" button.
2. **SocketIO**: The text is sent via WebSocket to the backend server.
3. **Speech Synthesis**: The server sends the text to the frontend, where it's spoken using the browser's `speechSynthesis` API.
4. **Avatar Animation**: The avatar's mouth opens and closes to simulate speech using GSAP (GreenSock Animation Platform).

## Endpoints

- `GET /`: Renders the main web page with the avatar and chat interface.
- `POST /trigger_speak`: Triggers speech synthesis on the backend by sending a JSON object containing the text to speak.
- `GET /static/<path:filename>`: Serves static files such as JavaScript, CSS, and images.
- `GET /model/shizuku/<path:filename>`: Serves model-related files like textures and motion data.

## Example Usage

- Enter some text in the input field and click "Speak".
- The Live2D avatar will animate and speak the entered text.
- You can send text through a WebSocket message by emitting a `speak` event.

## Contribution

Feel free to fork the repository, submit issues, and create pull requests. Contributions are welcome!

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

**Note**: You must have the Live2D model files and related resources to use the avatar animation functionality.
