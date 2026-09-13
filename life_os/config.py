import os
from pathlib import Path

from dotenv import load_dotenv

# Prefer repo-root .env; .env.local overrides if present
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")
load_dotenv(_root / ".env.local", override=True)

ADMIN_MAX = 10

# Default LLM stack: Gemini
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "gemini")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-3.6-flash")

# Optional Anthropic fallback (LLM_PROVIDER=anthropic)
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-4-8")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# HITL confidence threshold — below this Critic gates approval
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
