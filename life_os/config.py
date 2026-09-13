import os
from dotenv import load_dotenv

load_dotenv()

ADMIN_MAX = 10
LLM_MODEL = os.getenv("LLM_MODEL", "claude-opus-4-8")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# HITL confidence threshold — below this Critic gates approval
CONFIDENCE_THRESHOLD = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))
