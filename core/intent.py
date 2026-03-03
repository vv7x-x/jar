from typing import Literal

Intent = Literal["command", "question", "emotional", "casual"]


class IntentEngine:
    def __init__(self):
        pass

    def parse(self, text: str) -> Intent:
        t = text.strip()
        if t.endswith("?"):
            return "question"
        # simplistic command detection
        if any(t.lower().startswith(x) for x in ("open", "run", "execute", "activate", "فعل", "شغّل")):
            return "command"
        if any(word in t.lower() for word in ("i feel", "حزين", "حزن", "حلو")):
            return "emotional"
        return "casual"
