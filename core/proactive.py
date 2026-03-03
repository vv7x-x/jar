import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)


class ProactiveObserver:
    def __init__(self, brain, memory, personality, idle_trigger: int = 15 * 60):
        self.brain = brain
        self.memory = memory
        self.personality = personality
        self.idle_trigger = idle_trigger
        self._last_action = time.time()
        self._running = True

    async def run(self):
        while True:
            try:
                await asyncio.sleep(5)
                now = time.time()
                if now - self._last_action > self.idle_trigger:
                    # idle action
                    logger.info("User idle - making a subtle comment")
                    # TODO: query brain for a short phrase
                    self._last_action = now
                # More proactive checks can be added here
            except asyncio.CancelledError:
                break

    def touch(self):
        self._last_action = time.time()
