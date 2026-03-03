import asyncio
import logging
import requests
import os
import pyttsx3
from typing import Optional
from config import ELEVEN_API_KEY, PREFERRED_VOICE

logger = logging.getLogger(__name__)


class SpeechEngine:
    def __init__(self):
        self.eleven_key = ELEVEN_API_KEY
        self.voice = PREFERRED_VOICE
        self.local_engine = pyttsx3.init()

    async def speak(self, text: str, mood: Optional[str] = None):
        # Build voice settings based on mood
        settings = self._voice_profile_for_mood(mood)
        if self.eleven_key:
            try:
                self._eleven_speak(text, settings)
                return
            except Exception as e:
                logger.warning("ElevenLabs TTS failed: %s. Falling back to local TTS.", e)
        # Local TTS fallback
        await asyncio.get_event_loop().run_in_executor(None, self._local_speak, text)

    def _voice_profile_for_mood(self, mood: Optional[str]):
        profile = {"speed": 1.0, "pitch": 0.0, "stability": 0.75}
        if mood == "sad":
            profile.update({"speed": 0.9})
        if mood == "excited":
            profile.update({"speed": 1.15})
        return profile

    def _eleven_speak(self, text: str, settings: dict):
        # Minimal ElevenLabs example — user must provide API key
        url = "https://api.elevenlabs.io/v1/text-to-speech/" + self.voice
        headers = {"xi-api-key": self.eleven_key, "Content-Type": "application/json"}
        payload = {"text": text, "voice_settings": {"stability": settings.get("stability", 0.75), "similarity_boost": 0.75}}
        r = requests.post(url, json=payload, headers=headers, stream=True, timeout=15)
        r.raise_for_status()
        # Save received audio to temp and play via local engine if needed — placeholder
        logger.info("Received audio bytes from ElevenLabs (length=%d)", len(r.content))

    def _local_speak(self, text: str):
        self.local_engine.say(text)
        self.local_engine.runAndWait()
