import requests
import time
from twitchio.ext import commands
import asyncio
from dotenv import load_dotenv
import os

load_dotenv()

# Twitch CFG
TOKEN = os.getenv("TOKEN")
CLIENT_ID = os.getenv("CLIENT_ID")
BOT_NAME = os.getenv("BOT_NAME")
CHANNEL_NAME = [os.getenv("CHANNEL_NAME")]
EXTRA_DELAY_LISTENER = float(os.getenv("EXTRA_DELAY_LISTENER"))
NB_SPAM_MESSAGE = float(os.getenv("NB_SPAM_MESSAGE"))

# Avatar server URL
API_URL = os.getenv("API_URL")
API_URL_PORT = os.getenv("API_URL_PORT")

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
                response = requests.post(
                    f"{API_URL}:{API_URL_PORT}/process_message",
                    json={"message": user_input}
                )
                
                if response.status_code != 200:
                    print(f"Error from server: {response.status_code}")
                    print(f"Error response: {response.text}")
                    
            except Exception as e:
                print(f"Error sending message to server: {e}")

                await self._wait_for_extra_delay()
                self.processing = False

    async def _wait_for_extra_delay(self):
        await asyncio.sleep(self.extra_delay)

if __name__ == "__main__":
    bot = TwitchBot()
    bot.run()