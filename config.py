"""
config.py
---------
All the boring, changeable stuff lives here: app name, which Ollama model
to talk to, where Ollama is running, and where saved chats go.

Keeping this separate from main.py means you can swap models or point at
a different Ollama host without touching any application logic.
"""

import os

# --- App identity -----------------------------------------------------
APP_NAME = "DevMentor"
APP_TAGLINE = "your local programming assistant"

# --- Ollama connection --------------------------------------------------
# ollama.chat() defaults to http://localhost:11434, but we keep it
# explicit and overridable via an environment variable.
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")

# Default model used if the user does not pick one at startup (Bonus 1).
# IMPORTANT: Ollama model names include the tag (the part after the colon)
# and matching is exact - `ollama.chat(model="llama3.2")` looks for
# "llama3.2:latest" specifically, which 404s if you only pulled a
# different tag (e.g. "llama3.2:1b"). Run `ollama list` and use whatever
# it actually prints.
DEFAULT_MODEL = os.environ.get("DEVMENTOR_MODEL", "llama3.2:1b")

# Fallback list offered in the startup picker if `ollama.list()` can't be
# reached. Edit this to match whatever you've actually pulled locally.
# main.py prefers querying Ollama directly (get_installed_models()) so
# this list only matters as a last resort.
AVAILABLE_MODELS = [
    "llama3.2:1b",
    "qwen2.5:1.5b",
]

# --- Conversation controls --------------------------------------------
# A soft ceiling on how many *messages* (not tokens) we keep before we
# start trimming the oldest turns. See Bonus 4 discussion in the README
# for why this matters and better strategies than a blunt cutoff.
MAX_HISTORY_MESSAGES = 40

# --- Saved conversations (Bonus 2 / Bonus 3) ---------------------------
CONVERSATIONS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "conversations")
