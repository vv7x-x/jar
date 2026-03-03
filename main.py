import asyncio
import logging
from core.brain import Brain
from core.memory import VectorMemory
from core.intent import IntentEngine
from core.emotion import EmotionAnalyzer
from core.personality import PersonalityEngine
from core.proactive import ProactiveObserver
from core.speech import SpeechEngine

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")


async def main():
    brain = Brain()
    memory = VectorMemory()
    intent = IntentEngine()
    emotion = EmotionAnalyzer()
    personality = PersonalityEngine()
    speech = SpeechEngine()

    observer = ProactiveObserver(brain=brain, memory=memory, personality=personality)
    observer_task = asyncio.create_task(observer.run())

    print("BLACK JARVIS ready. Type 'exit' to quit.")
    try:
        while True:
            text = await asyncio.get_event_loop().run_in_executor(None, input, "> ")
            if not text:
                continue
            if text.strip().lower() in ("exit", "quit"):
                break

            # Intent
            it = intent.parse(text)

            # Emotion
            mood = emotion.analyze_text(text)
            personality.adjust_for_mood(mood)

            # Query brain
            resp = await brain.generate_text(prompt=text, stream=False)
            print(resp)

            # Speak response
            await speech.speak(resp, mood=mood)

    finally:
        observer_task.cancel()


if __name__ == "__main__":
    asyncio.run(main())
