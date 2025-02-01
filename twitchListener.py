import time
from twitchio.ext import commands
import asyncio
from dotenv import load_dotenv
import os
from socketio import Client

load_dotenv()

# Twitch CFG
TOKEN = os.getenv("TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
BOT_NAME = os.getenv("BOT_NAME")
CHANNEL_NAME = [os.getenv("CHANNEL_NAME")]
EXTRA_DELAY_LISTENER = float(os.getenv("EXTRA_DELAY_LISTENER"))
NB_SPAM_MESSAGE = float(os.getenv("NB_SPAM_MESSAGE"))

# Avatar server URL
API_URL = os.getenv("API_URL", "localhost")
API_URL_PORT = os.getenv("API_URL_PORT", "5000")

# Debug prints to check the values
print(f"API_URL: {API_URL}")
print(f"API_URL_PORT: {API_URL_PORT}")

# Initialize SocketIO client with retry mechanism
socket = Client()

def connect_socket():
    retries = 5
    for attempt in range(retries):
        try:
            socket.connect(f"{API_URL}:{API_URL_PORT}")
            print("Connected to WebSocket server")
            break
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    else:
        print("Failed to connect to WebSocket server after several attempts")

connect_socket()

class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            client_id=CLIENT_ID,
            nick=BOT_NAME,
            prefix="!ai",
            initial_channels=CHANNEL_NAME,
        )
        
        self.processing = False
        self.processing_time = 0
        self.user_last_message = {}
        self.spam_time_window = NB_SPAM_MESSAGE
        self.extra_delay = EXTRA_DELAY_LISTENER

    async def event_ready(self):
        print(f"Logged in as | {self.nick}")
        print(f"Connected to channel | {CHANNEL_NAME}")

    async def event_message(self, message):
        if message.echo:
            return

        current_time = time.time()
        if self.processing and current_time - self.processing_time < self.extra_delay:
            return

        user_id = message.author.name
        if user_id in self.user_last_message:
            last_message, last_time = self.user_last_message[user_id]
            if current_time - last_time < self.spam_time_window and message.content == last_message:
                print(f"Spam detected from {user_id}: {message.content}")
                return

        self.user_last_message[user_id] = (message.content, current_time)

        if message.content.startswith('!ai'):
            user_input = message.content[4:].strip()
            if not user_input:
                await message.channel.send(f"{message.author.name}, please provide a valid question.")
                return

            self.processing = True
            self.processing_time = current_time

            try:
                # Emit the AI request to the WebSocket server
                socket.emit('trigger_ai_request', {'message': user_input})
                
                # Emit username and question to WebSocket server
                socket.emit('display_question', {'username': message.author.name, 'question': user_input})
                    
            except Exception as e:
                print(f"Error sending message to server: {e}")

                await self._wait_for_extra_delay()
                self.processing = False

    async def _wait_for_extra_delay(self):
        await asyncio.sleep(self.extra_delay)

if __name__ == "__main__":
    bot = TwitchBot()
    bot.run()
    socket.disconnect()