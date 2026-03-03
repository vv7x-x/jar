import time
from typing import Dict


class PersonalityEngine:
    def __init__(self):
        self.mood = "neutral"
        self.roast_level = 1
        self.last_active = time.time()
        self.roast_enabled = True

    def adjust_for_mood(self, mood: str):
        self.mood = mood
        if mood == "sad":
            self.roast_level = max(0, self.roast_level - 1)
        elif mood == "excited":
            self.roast_level += 1

    def should_roast(self, user_confident: bool) -> bool:
        if not self.roast_enabled:
            return False
        return self.roast_level > 0 and user_confident

    def register_inactivity(self):
        now = time.time()
        if now - self.last_active > 20 * 60:
            return True
        return False

    def update_activity(self):
        self.last_active = time.time()
