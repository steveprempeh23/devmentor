#!/usr/bin/env python3
"""
main.py
-------
DevMentor: a local, command-line conversational AI assistant built on top
of Ollama.

This file owns: startup, the interactive loop, wiring user input to the
Ollama API, and the conversation-control commands (/reset, /history,
/exit, /save, /load, /mode).

It deliberately does NOT own: what the system prompt says (prompts.py) or
what model/settings we use (config.py). Keeping those separate is the
whole point of the assignment — see the README's Architecture section.
"""

import sys
import json
import datetime

import config
import prompts

try:
    import ollama
except ImportError:  # pragma: no cover - guidance for the user, not logic
    print(
        "The 'ollama' Python package isn't installed.\n"
        "Run:  pip install -r requirements.txt\n"
    )
    sys.exit(1)


# ---------------------------------------------------------------------
# Application state
# ---------------------------------------------------------------------
# Ollama's API is stateless: every call only knows what's in THIS
# request. "Memory" is an illusion we create by resending the full
# message list every single turn. `messages` below is that list, and it
# is the entire memory of the conversation. See README > Memory
# Investigation for more on this.

def build_system_message(system_prompt: str) -> dict:
    return {"role": "system", "content": system_prompt}


def new_conversation(system_prompt: str) -> list:
    """Start a fresh conversation containing only the system message."""
    return [build_system_message(system_prompt)]


# ---------------------------------------------------------------------
# Core Ollama interaction
# ---------------------------------------------------------------------

def get_ai_response(messages: list, model: str) -> str:
    """
    Send the full message list to Ollama and return the assistant's
    reply text. Raises the underlying exception on failure — callers are
    expected to handle it (see the try/except in the main loop), which
    keeps this function simple and testable.
    """
    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]


# ---------------------------------------------------------------------
# Conversation controls
# ---------------------------------------------------------------------

def reset_conversation(system_prompt: str) -> list:
    print("Conversation reset.")
    return new_conversation(system_prompt)


def display_history(messages: list) -> None:
    """
    Print the chat turns only — never the system message, which is
    configuration, not a chat turn the user typed or received.
    """
    turns = [m for m in messages if m["role"] != "system"]
    if not turns:
        print("(no messages yet)")
        return
    for i, msg in enumerate(turns, start=1):
        role = "USER" if msg["role"] == "user" else "ASSISTANT"
        print(f"{i}. {role}: {msg['content']}")


def trim_history(messages: list, max_messages: int) -> list:
    """
    Very blunt context-window management: once we exceed max_messages,
    drop the oldest non-system turns. Always keeps the system message.
    Real strategies (summarisation, sliding windows, token-aware
    trimming) are discussed in the README's Bonus 4 write-up.
    """
    system_msgs = [m for m in messages if m["role"] == "system"]
    turns = [m for m in messages if m["role"] != "system"]
    if len(turns) > max_messages:
        turns = turns[-max_messages:]
    return system_msgs + turns


def save_conversation(messages: list) -> str:
    import os
    os.makedirs(config.CONVERSATIONS_DIR, exist_ok=True)
    timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
    filename = f"chat_{timestamp}.json"
    path = os.path.join(config.CONVERSATIONS_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(messages, f, indent=2)
    return filename


def load_conversation(filename: str):
    import os
    path = filename
    if not os.path.isabs(path):
        path = os.path.join(config.CONVERSATIONS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        loaded = json.load(f)
    # Must restore the FULL message list, system prompt included —
    # that's what gives the model back its "memory" and behaviour.
    return loaded


# ---------------------------------------------------------------------
# Startup helpers
# ---------------------------------------------------------------------

def choose_model() -> str:
    """Bonus 1: let the user pick an installed Ollama model at startup."""
    print("Available models:")
    for i, name in enumerate(config.AVAILABLE_MODELS, start=1):
        print(f"{i}. {name}")
    choice = input(f"Select model [1-{len(config.AVAILABLE_MODELS)}] "
                    f"(Enter for default '{config.DEFAULT_MODEL}'): ").strip()
    if not choice:
        return config.DEFAULT_MODEL
    if choice.isdigit() and 1 <= int(choice) <= len(config.AVAILABLE_MODELS):
        return config.AVAILABLE_MODELS[int(choice) - 1]
    print(f"Didn't recognise '{choice}', using default '{config.DEFAULT_MODEL}'.")
    return config.DEFAULT_MODEL


def choose_personality() -> str:
    """Bonus 5: let the user pick a personality mode at startup."""
    print("\nChoose a mode:")
    print("0. Default (DevMentor)")
    for key, mode in prompts.PERSONALITY_MODES.items():
        print(f"{key}. {mode['name']}")
    choice = input("Select mode (Enter for Default): ").strip()
    if choice in prompts.PERSONALITY_MODES:
        return prompts.PERSONALITY_MODES[choice]["prompt"]
    return prompts.DEFAULT_SYSTEM_PROMPT


def check_ollama_connection(model: str) -> bool:
    """
    Fail fast and politely if Ollama isn't reachable, rather than letting
    the user discover it mid-conversation with a raw traceback.
    """
    try:
        ollama.list()
        return True
    except Exception:
        print(
            "Unable to connect to Ollama.\n"
            "Make sure Ollama is running (try `ollama serve` in another "
            "terminal) and try again."
        )
        return False


# ---------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------

def print_banner(model: str) -> None:
    title = f" {config.APP_NAME} AI Assistant "
    print("=" * 12 + title + "=" * 12)
    print(f"Model: {model}   |   Commands: /reset  /history  /save  /load <file>  /exit")
    print("-" * (24 + len(title)))


def main() -> None:
    model = choose_model()

    if not check_ollama_connection(model):
        sys.exit(1)

    system_prompt = choose_personality()
    messages = new_conversation(system_prompt)

    print_banner(model)

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        # --- Empty input handling -------------------------------------
        if not user_input:
            print("(empty input ignored — type something, or /exit to quit)")
            continue

        # --- Commands ----------------------------------------------------
        if user_input == "/exit":
            print("Goodbye!")
            break

        if user_input == "/reset":
            messages = reset_conversation(system_prompt)
            continue

        if user_input == "/history":
            display_history(messages)
            continue

        if user_input == "/save":
            try:
                filename = save_conversation(messages)
                print(f"Conversation saved to: {config.CONVERSATIONS_DIR}/{filename}")
            except OSError as e:
                print(f"Couldn't save conversation: {e}")
            continue

        if user_input.startswith("/load"):
            parts = user_input.split(maxsplit=1)
            if len(parts) != 2:
                print("Usage: /load <filename>")
                continue
            try:
                messages = load_conversation(parts[1])
                print(f"Loaded conversation from {parts[1]}.")
            except (FileNotFoundError, json.JSONDecodeError) as e:
                print(f"Couldn't load '{parts[1]}': {e}")
            continue

        # --- Ordinary chat turn -----------------------------------------
        messages.append({"role": "user", "content": user_input})
        messages = trim_history(messages, config.MAX_HISTORY_MESSAGES)

        try:
            reply = get_ai_response(messages, model)
        except ConnectionError:
            print("Unable to connect to Ollama. Make sure Ollama is running and try again.")
            messages.pop()  # don't keep a user turn that got no reply
            continue
        except Exception as e:
            # Covers ollama.ResponseError (e.g. unknown/missing model)
            # and anything else unexpected, without a raw traceback.
            msg = str(e)
            if "not found" in msg.lower() or "model" in msg.lower():
                print(
                    f"There's a problem with the model '{model}': {msg}\n"
                    f"Try `ollama pull {model}` or pick a different model."
                )
            else:
                print(f"Something went wrong talking to the model: {msg}")
            messages.pop()
            continue

        print(f"AI: {reply}")
        messages.append({"role": "assistant", "content": reply})


if __name__ == "__main__":
    main()
