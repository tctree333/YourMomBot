import logging
import time
import asyncio
from pathlib import Path
from datetime import datetime

import discord

from src.yourmumbot.YourMumModel import YourMumModel
from helpers.logging import log_memory_used, reset_logging
import constants as cst


reset_logging()

# Args
log_level = logging.INFO

# setup logger
current_time = datetime.now().strftime('%d-%m-%y-%H:%M:%S')
filename = f"{cst.LOGS_DIR}/main/yourmumbot-{current_time}.log"
Path(filename).parent.mkdir(parents=True, exist_ok=True)
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=log_level,
    filename=filename,
    format=cst.LOG_FORMAT)
logger.setLevel(log_level)


class YourMumClient(discord.Client):
    def __init__(self,
                 corrector="language_tools",
                 log_every=cst.LOG_EVERY,
                 *args,
                 **kwargs):
        super().__init__(*args, **kwargs)
        self.model = YourMumModel(corrector=corrector, logger=logger)
        self.corrector = corrector

        assert log_every >= 1
        self.log_every = log_every
        self.msg_count = 0

        self.connections = 0
        self.connections_hist = 0

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.model.__exit__(*args)

    @staticmethod
    def block(text, original):
        yourmum = "your mum"
        _text = text.lower().replace(" ", "")
        _yourmum = yourmum.lower().replace(" ", "")
        _original = original.lower().replace(" ", "")
        if text == "":
            return True
        if _text == _original:
            return True
        if _text == _yourmum:
            return True
        # sanity check
        if not 'your mum' in text.lower():
            return True
        return False

    async def dec_connections_hist(self, duration):
        await asyncio.sleep(duration)
        self.connections_hist -= 1

    async def keep_model_warm(self):
        # run every ${cst.STAY_WARM_PERIOD} seconds
        while True:
            if self.connections_hist < 1:
                self.model.warm_up()
                logger.info("Keeping warm!")
            await asyncio.sleep(cst.STAY_WARM_PERIOD)

    async def on_ready(self):
        print(f'{self.user} is connected to the following guilds:')
        for guild in self.guilds:
            print(f'{guild.name} (id: {guild.id})')
        print(f'Running with corrector {self.corrector}')
        print("Warming up the model...")
        self.model.warm_up()
        print("Ready!")
        print("Keeping model warm...")
        asyncio.create_task(self.keep_model_warm())

    async def on_message(self, message):
        if not message.author.bot:
            # prevent server from overloading
            if self.connections >= cst.MAX_CONNECTIONS:
                return

            # time inference latency
            start = time.time()

            # keep track of no of connections
            self.connections += 1
            self.connections_hist += 1

            try:
                # compute response
                content = message.content
                yourmumify_content = " ".join(
                    list(self.model.yourmumify(content)))

                # log memory usage (logging total memory is expensive)
                # so only log every n requests
                if self.msg_count % self.log_every == 0:
                    self.msg_count = 0
                    logger.info(log_memory_used())
                self.msg_count += 1

                logger.info(f"Compute latency: {(time.time()-start):.4}s")
                if not self.block(yourmumify_content, content):
                    logger.info(f"Yourmumified: {yourmumify_content}")
                    await message.channel.send(
                        content=yourmumify_content,
                        reference=message,
                        mention_author=False)
                logger.info(f"Total latency: {(time.time()-start):.4}s")
            finally:
                # keep track of no of connections
                self.connections -= 1
                asyncio.create_task(
                    self.dec_connections_hist(cst.STAY_WARM_PERIOD))
