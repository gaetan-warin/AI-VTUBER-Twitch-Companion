"""Twitch chat bot for handling follow/sub events and AI interactions.

This module implements a Twitch bot that listens for chat messages, follows,
and subscriptions, forwarding them to a WebSocket server for AI processing
and avatar animations.
"""

import asyncio
import os
import time
import bleach
from dotenv import load_dotenv
from socketio import Client
from twitchio.ext import commands

# Load default .env file
load_dotenv(encoding='latin1')

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

BOT_NAME_FOLLOW_SUB = "botwarga"
KEY_WORD_FOLLOW = "New FOLLOW(S)"
KEY_WORD_SUB = "NEW SUB"
DELIMITER_NAME = "{"
DELIMITER_NAME_END = "}"

# Initialize SocketIO client with retry mechanism
socket = Client()

def connect_socket():
    """Establish connection to WebSocket server with retry mechanism.

    Attempts to connect up to 10 times with 2-second delay between retries.
    """
    retries = 10
    for attempt in range(retries):
        try:
            socket.connect(f"{API_URL}:{API_URL_PORT}")
            print("Connected to WebSocket server")
            break
        except (ConnectionError, TimeoutError) as e:
            print(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    else:
        print("Failed to connect to WebSocket server after several attempts")

connect_socket()

class TwitchBot(commands.Bot):
    """Twitch chat bot that handles messages and events.

    Manages chat interactions, follows, subscriptions, and AI request processing
    with built-in spam protection and delay management.
    """

    def __init__(self):
        """Initialize the Twitch bot with configuration and state variables."""
        super().__init__(
            token=TOKEN,
            client_id=CLIENT_ID,
            nick=BOT_NAME,
            prefix="",
            initial_channels=CHANNEL_NAME,
        )

        self.processing = False
        self.processing_time = 0
        self.user_last_message = {}
        self.spam_time_window = NB_SPAM_MESSAGE
        self.extra_delay = EXTRA_DELAY_LISTENER

    async def event_ready(self):
        """Handle bot ready event, logging connection status."""
        print(f"Logged in as | {self.nick}")
        print(f"Connected to channel | {CHANNEL_NAME}")

    async def event_message(self, message):
        """Process incoming Twitch chat messages.

        Handles follow/sub events, spam detection, and AI requests.

        Args:
            message: The incoming Twitch chat message object
        """
        if message.echo:
            return

        if message.author.name == BOT_NAME_FOLLOW_SUB and KEY_WORD_FOLLOW in message.content:
            follower_name = message.content.split(DELIMITER_NAME)[1].split(DELIMITER_NAME_END)[0]
            text = f"Wonderful, we have a new follower. Thank you: {follower_name}"
            socket.emit('speak', {'text': text})
            socket.emit('trigger_event', {'event_type': 'follow', 'username': follower_name})
            return

        if message.author.name == BOT_NAME_FOLLOW_SUB and KEY_WORD_SUB in message.content:
            follower_name = message.content.split(DELIMITER_NAME)[1].split(DELIMITER_NAME_END)[0]
            text = f"Incredible, we have a new subscriber. Thank you so much: {follower_name}"
            socket.emit('speak', {'text': text})
            socket.emit('trigger_event', {'event_type': 'sub', 'username': follower_name})
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
                msg = f"{message.author.name}, please provide a valid question."
                await message.channel.send(msg)
                return

            self.processing = True
            self.processing_time = current_time

            try:
                # Sanitize the user input
                sanitized_input = bleach.clean(user_input)

                # Emit the AI request to the WebSocket server
                socket.emit('trigger_ai_request', {'message': sanitized_input})

                # Emit username and question to WebSocket server
                data = {'username': message.author.name, 'question': sanitized_input}
                socket.emit('display_question', data)

            except (ConnectionError, TimeoutError) as e:
                print(f"Socket connection error: {e}")
                await self._wait_for_extra_delay()
                self.processing = False
            except ValueError as e:
                print(f"Data processing error: {e}")
                await self._wait_for_extra_delay()
                self.processing = False

    async def _wait_for_extra_delay(self):
        """Wait for the configured delay between message processing."""
        await asyncio.sleep(self.extra_delay)

if __name__ == "__main__":
    bot = TwitchBot()
    bot.run()
    socket.disconnect()
