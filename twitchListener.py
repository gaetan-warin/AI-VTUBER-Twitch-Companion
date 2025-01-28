import requests
import json
import re
import logging
from twitchio.ext import commands
import asyncio
import time
import websockets

CLIENT_ID = 'gp762nuuoqcoxypju8c569th9wz7q5'
TOKEN = "w8luqg6ddftxrqhtniyvg5l9btia11"
CHANNEL_NAME = ['botwarga']
LIMIT_ANSWER = 200
TTS_WEBSOCKET_URL = "ws://localhost:5000/tts"  # Replace with your WebSocket server URL

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class TwitchBot(commands.Bot):
    def __init__(self):
        super().__init__(
            token=TOKEN,
            client_id=CLIENT_ID,
            nick='AI BOTWarga',
            prefix="!ai",
            initial_channels=CHANNEL_NAME,
        )
        self.processing = False
        self.processing_time = 0
        self.user_last_message = {}
        self.spam_time_window = 5
        self.extra_delay = 3

    async def event_ready(self):
        logger.info(f"Logged in as | {self.nick}")
        logger.info(f"Connected to channel | {CHANNEL_NAME}")

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
                logger.info(f"Spam detected from {user_id}: {message.content}")
                return

        self.user_last_message[user_id] = (message.content, current_time)
        logger.info(f"**Message from {message.author.name}: {message.content}")

        if message.content.startswith('!ai'):
            user_input = message.content[4:].strip()
            if not user_input:
                await message.channel.send(f"{message.author.name}, please provide a valid question.")
                return

            self.processing = True
            self.processing_time = current_time

            response = self.generate_ai_response(user_input)
            for chunk in self.split_message(response):
                await message.channel.send(f"{message.author.name}, {chunk}")
                logger.info(f"*** BOTWarga answer: {chunk}")
                await self.send_to_tts(chunk)

            await self._wait_for_extra_delay()
            self.processing = False

    async def send_to_tts(self, text):
        """Send text to the TTS WebSocket server."""
        try:
            async with websockets.connect(TTS_WEBSOCKET_URL) as websocket:
                await websocket.send(json.dumps({"text": text}))
                logger.info(f"Sent to TTS WebSocket: {text}")
        except Exception as e:
            logger.error(f"Error sending to TTS WebSocket: {e}")

    async def _wait_for_extra_delay(self):
        await asyncio.sleep(self.extra_delay)

    def split_message(self, message, limit=300):
        chunks = []
        while len(message) > limit:
            split_point = max(
                message.rfind('. ', 0, limit),
                message.rfind('? ', 0, limit),
                message.rfind('! ', 0, limit)
            )
            if split_point == -1:
                split_point = limit
            chunks.append(message[:split_point].strip())
            message = message[split_point:].strip()
        if message:
            chunks.append(message)
        return chunks

    def generate_ai_response(self, user_input):
        try:
            user_input = f"Respond in less than {LIMIT_ANSWER} characters and be as consistent as possible. Your prompt is: {user_input}."
            logger.debug(f"User input: {user_input}")
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={"model": "deepseek-r1:1.5b", "prompt": user_input},
            )

            if response.status_code != 200:
                logger.error(f"Failed to get a response from the AI API. Status code: {response.status_code}")
                return f"Error: Failed to get a response from the AI API. Status code: {response.status_code}"

            full_response = []
            for line in response.text.splitlines():
                try:
                    response_data = json.loads(line)
                    if response_data.get('done', False):
                        full_response.append(response_data.get('response', ''))
                        break
                    else:
                        full_response.append(response_data.get('response', ''))
                except Exception as e:
                    logger.error(f"Error parsing line: {e}")
            final_response = ''.join(full_response).strip()
            cleaned_response = self.clean_response(final_response)
            return cleaned_response
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return f"Error: {str(e)}"

    def clean_response(self, response):
        response = re.sub(r'<think>\s*.*?\s*</think>', '', response, flags=re.DOTALL)
        response = re.sub(r'[^\x00-\x7F]+', '', response)
        response = re.sub(r'\\_\\_\\_', '', response)
        response = re.sub(r'\s+', ' ', response).strip()
        return response

if __name__ == "__main__":
    bot = TwitchBot()
    bot.run()
