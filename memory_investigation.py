#!/usr/bin/env python3
"""
memory_investigation.py
------------------------
Part 8 — Memory Investigation.

Runs a scripted chat, asks the model to recall a fact, then DROPS the
early messages that contain that fact from the message list and asks
again — proving that "memory" is really just whatever we choose to
resend, not something the model retains internally.

Usage:
    python memory_investigation.py
"""

import ollama
import config

MODEL = config.DEFAULT_MODEL
SYSTEM_PROMPT = "You are a helpful programming assistant."


def chat(messages):
    response = ollama.chat(model=MODEL, messages=messages)
    return response["message"]["content"]


def main():
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    turns = [
        "My favorite programming language is Python.",
        "Explain interfaces.",
        "What is my favorite programming language?",
    ]

    print("=== Phase 1: full history kept ===")
    for turn in turns:
        messages.append({"role": "user", "content": turn})
        reply = chat(messages)
        messages.append({"role": "assistant", "content": reply})
        print(f"\nUser: {turn}\nAI: {reply}")

    print("\n\n=== Phase 2: early messages (the fact) dropped ===")
    # Drop the system message aside, drop the first user+assistant pair
    # that actually contains the fact, keep the rest.
    system_msg = messages[0]
    remaining = messages[1:]
    # remove the first user/assistant pair (index 0 and 1 of `remaining`)
    trimmed = remaining[2:]
    trimmed_messages = [system_msg] + trimmed

    follow_up = "What is my favorite programming language?"
    trimmed_messages.append({"role": "user", "content": follow_up})
    reply = chat(trimmed_messages)
    print(f"\nUser: {follow_up}\nAI: {reply}")

    print(
        "\n\nObservation: once the message containing the fact is no "
        "longer in the list we send, the model has no way to know it — "
        "it isn't 'remembered' anywhere except in the message history "
        "our application chooses to resend on each call."
    )


if __name__ == "__main__":
    main()
