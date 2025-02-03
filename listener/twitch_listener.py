"""Twitch chat bot for handling follow/sub events and AI interactions.

This module implements a Twitch bot that listens for chat messages, follows,
and subscriptions, forwarding them to a WebSocket server for AI processing
and avatar animations.
"""

import asyncio
import os
import time
import bleach
import logging
from dotenv import load_dotenv
from socketio import Client
from twitchio.ext import commands

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load configuration
load_dotenv(encoding='latin1')

class Config:
    def __init__(self):
        self.fields = [
            'TWITCH_TOKEN', 'CLIENT_ID', 'CHANNEL_NAME', 'EXTRA_DELAY_LISTENER',
            'NB_SPAM_MESSAGE', 'API_URL', 'API_URL_PORT', 'BOT_NAME_FOLLOW_SUB',
            'KEY_WORD_FOLLOW', 'KEY_WORD_SUB', 'DELIMITER_NAME', 'DELIMITER_NAME_END'
        ]
        self.load()

    def load(self):
        for field in self.fields:
            value = os.getenv(field)
            setattr(self, field.lower(), value)
        
        # Convert numeric values
        self.extra_delay_listener = float(self.extra_delay_listener)
        self.nb_spam_message = float(self.nb_spam_message)
        self.channel_name = [self.channel_name]  # Convert to list for twitchio

    def update(self, **kwargs):
        for key, value in kwargs.items():
            if key.upper() in self.fields:
                setattr(self, key.lower(), value)
        
        # Convert numeric values
        if 'EXTRA_DELAY_LISTENER' in kwargs:
            self.extra_delay_listener = float(self.extra_delay_listener)
        if 'NB_SPAM_MESSAGE' in kwargs:
            self.nb_spam_message = float(self.nb_spam_message)

config = Config()

# Initialize SocketIO client
socket = Client()

def connect_socket():
    retries = 10
    for attempt in range(retries):
        try:
            socket.connect(f"{config.api_url}:{config.api_url_port}")
            logger.info("Connected to WebSocket server")
            break
        except (ConnectionError, TimeoutError) as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {e}")
            time.sleep(2)
    else:
        logger.error("Failed to connect to WebSocket server after several attempts")

connect_socket()

class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=config.twitch_token,
            client_id=config.client_id,
            prefix="",
            initial_channels=config.channel_name,
        )
        self.processing = False
        self.processing_time = 0
        self.user_last_message = {}

    async def event_ready(self):
        logger.info(f"Logged in as | {self.nick}")
        logger.info(f"Connected to channel | {config.channel_name}")

    async def event_message(self, message):
        if message.echo:
            return

        if self._handle_follow_sub_event(message):
            return

        await self._handle_user_message(message)

    def _handle_follow_sub_event(self, message):
        if message.author.name == config.bot_name_follow_sub:
            if config.key_word_follow in message.content:
                self._emit_celebration('follow', message.content)
                return True
            elif config.key_word_sub in message.content:
                self._emit_celebration('sub', message.content)
                return True
        return False

    def _emit_celebration(self, event_type, content):
        name = content.split(config.delimiter_name)[1].split(config.delimiter_name_end)[0]
        text = f"{'Wonderful, we have a new follower' if event_type == 'follow' else 'Incredible, we have a new subscriber'}. Thank you: {name}"
        socket.emit('speak', {'text': text})
        socket.emit('trigger_event', {'event_type': event_type, 'username': name})

    async def _handle_user_message(self, message):
        current_time = time.time()
        if self.processing and current_time - self.processing_time < config.extra_delay_listener:
            return

        user_id = message.author.name
        if self._is_spam(user_id, message.content, current_time):
            logger.info(f"Spam detected from {user_id}: {message.content}")
            return

        self.user_last_message[user_id] = (message.content, current_time)

        if message.content.startswith('!ai'):
            await self._process_ai_request(message)

    def _is_spam(self, user_id, content, current_time):
        if user_id in self.user_last_message:
            last_message, last_time = self.user_last_message[user_id]
            return (current_time - last_time < config.nb_spam_message and content == last_message)
        return False

    async def _process_ai_request(self, message):
        user_input = message.content[4:].strip()
        if not user_input:
            await message.channel.send(f"{message.author.name}, please provide a valid question.")
            return

        self.processing = True
        self.processing_time = time.time()

        try:
            sanitized_input = bleach.clean(user_input)
            socket.emit('trigger_ai_request', {'message': sanitized_input})
            socket.emit('display_question', {'username': message.author.name, 'question': sanitized_input})
        except Exception as e:
            logger.error(f"Error processing AI request: {e}")
        finally:
            await asyncio.sleep(config.extra_delay_listener)
            self.processing = False

if __name__ == "__main__":
    bot = TwitchBot()

    @socket.on('update_twitch_config')
    def handle_config_update(data):
        try:
            config.update(**data)
            # Update bot attributes that depend on config
            bot.extra_delay_listener = config.extra_delay_listener
            bot.nb_spam_message = config.nb_spam_message
            logger.info("Twitch listener configuration updated successfully")
        except Exception as e:
            logger.error(f"Error updating twitch listener configuration: {e}")

    bot.run()
    socket.disconnect()
