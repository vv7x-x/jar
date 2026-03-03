from typing import Literal
import re

Mood = Literal["calm", "stressed", "sad", "angry", "excited", "neutral"]


class EmotionAnalyzer:
    def __init__(self):
        # Simple keyword-based analyzer; extend with voice features later
        self.keyword_map = {
            "sad": ["حزين", "حزينة", "حزن", "depressed", "sad"],
            "angry": ["زعلان", "غضب", "angry", "mad"],
            "excited": ["مبسوط", "فرحان", "excited", "wow"],
            "stressed": ["مضغوط", "توتر", "stressed", "anx"],
        }

    def analyze_text(self, text: str) -> Mood:
        low = text.lower()
        for mood, kws in self.keyword_map.items():
            for k in kws:
                if k in low:
                    return mood  # type: ignore
        return "neutral"
