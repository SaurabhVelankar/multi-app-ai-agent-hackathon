import os
from pathlib import Path

from dotenv import load_dotenv

# Prefer repo-root .env; .env.local overrides if present
_root = Path(__file__).resolve().parent.parent
load_dotenv(_root / ".env")
load_dotenv(_root / ".env.local", override=True)

ADMIN_MAX = int(os.getenv("ADMIN_MAX", "10"))
FAMILY_ID = os.getenv("FAMILY_ID", "default")
HITL_POLICY = os.getenv("HITL_POLICY", "any_of")

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

# Shared Google OAuth client (per-admin tokens live under .oauth/{admin_id}_google.json)
GOOGLE_OAUTH_CLIENT_ID = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_OAUTH_CLIENT_SECRET = os.getenv("GOOGLE_OAUTH_CLIENT_SECRET", "")
GOOGLE_OAUTH_REDIRECT_URI = os.getenv(
    "GOOGLE_OAUTH_REDIRECT_URI", "http://localhost:8000/oauth/google/callback"
)
