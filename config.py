from dotenv import load_dotenv
import os

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_PROJECT_ID = os.getenv("GEMINI_PROJECT_ID")

ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")

PREFERRED_VOICE = os.getenv("PREFERRED_VOICE", "jarvis_egypt_elite")
LANG = os.getenv("LANG", "ar-EG")

RETRY_MAX = int(os.getenv("RETRY_MAX", "3"))
RETRY_BASE = float(os.getenv("RETRY_BASE", "0.5"))
