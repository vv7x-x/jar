BLACK JARVIS — prototype

This repository provides a scaffolding for "BLACK JARVIS" — a semi-autonomous AI desktop assistant powered by Google Gemini (via the official google-genai SDK).

Features included in the scaffold:
- Async Gemini wrapper with retry and streaming placeholders
- FAISS-backed local memory (embeddings via sentence-transformers fallback)
- Emotion, intent, personality engine skeletons
- ElevenLabs TTS integration optional with local TTS fallback
- UI placeholders (hologram/particles/gestures)

See `main.py` and `core/` for code.

Setup
1. Copy `.env.example` to `.env` and fill keys.
2. Create virtualenv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Run
```bash
python main.py
```

This is an early scaffold — many modules contain TODOs and placeholders for integrating the official SDK and hardware.
# jar