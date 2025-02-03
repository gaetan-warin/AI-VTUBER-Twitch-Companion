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
            prefix="",
            initial_channels=CHANNEL_NAME,
        )

        self.processing = False
        self.processing_time = 0
        self.user_last_message = {}
        self.spam_time_window = NB_SPAM_MESSAGE
        self.extra_delay = EXTRA_DELAY_LISTENER
        self.bot_name_follow_sub = BOT_NAME_FOLLOW_SUB
        self.key_word_follow = KEY_WORD_FOLLOW
        self.key_word_sub = KEY_WORD_SUB
        self.delimiter_name = DELIMITER_NAME
        self.delimiter_name_end = DELIMITER_NAME_END

    def update(self, **kwargs):
        """Update bot configuration values.

        Args:
            **kwargs: Configuration key-value pairs to update
        """
        config_map = {
            'EXTRA_DELAY_LISTENER': ('extra_delay', float),
            'NB_SPAM_MESSAGE': ('spam_time_window', float),
            'BOT_NAME_FOLLOW_SUB': ('bot_name_follow_sub', str),
            'KEY_WORD_FOLLOW': ('key_word_follow', str),
            'KEY_WORD_SUB': ('key_word_sub', str),
            'DELIMITER_NAME': ('delimiter_name', str),
            'DELIMITER_NAME_END': ('delimiter_name_end', str)
        }

        for key, value in kwargs.items():
            if key in config_map:
                attr_name, converter = config_map[key]
                try:
                    setattr(self, attr_name, converter(value))
                except (ValueError, TypeError) as e:
                    print(f"Error updating {key}: {e}")

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

        if message.author.name == self.bot_name_follow_sub and self.key_word_follow in message.content:
            follower_name = message.content.split(self.delimiter_name)[1].split(self.delimiter_name_end)[0]
            text = f"Wonderful, we have a new follower. Thank you: {follower_name}"
            socket.emit('speak', {'text': text})
            socket.emit('trigger_event', {'event_type': 'follow', 'username': follower_name})
            return

        if message.author.name == self.bot_name_follow_sub and self.key_word_sub in message.content:
            follower_name = message.content.split(self.delimiter_name)[1].split(self.delimiter_name_end)[0]
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

    @socket.on('update_twitch_config')
    def handle_config_update(data):
        """Handle real-time configuration updates from the web interface."""
        try:
            bot.update(**data)
            print("Twitch listener configuration updated successfully")
        except (ValueError, TypeError) as e:
            print(f"Error updating twitch listener configuration: {e}")

    bot.run()
    socket.disconnect()
