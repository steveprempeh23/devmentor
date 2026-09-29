#!/usr/bin/env python3
"""
memory_investigation.py
------------------------
Part 8 - Memory Investigation.

Goal: prove, empirically, that Ollama has no memory of its own. Whatever
looks like "the assistant remembers" is entirely a product of us
resending the message history ourselves.

Phase 1 - a 3-turn conversation, full history kept, ending by asking the
          model to recall a fact it was told two turns earlier.
Phase 2 - the SAME final question, but sent with the fact-bearing turn
          explicitly removed from the message list first.

To make this genuinely convincing (not just "trust me"), the script
prints the EXACT messages list being sent to Ollama immediately before
every call. You should be able to look at that printout and see for
yourself whether the fact is present or absent - no guessing.

Usage:
    python memory_investigation.py
"""

import sys
import json

import ollama
import config

# Windows terminals can choke on non-ASCII characters small local models
# sometimes produce (em-dashes, math symbols, etc). Without this, such a
# character can crash the whole script mid-run with UnicodeEncodeError.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

MODEL = config.DEFAULT_MODEL
SYSTEM_PROMPT = "You are a helpful programming assistant. Keep answers brief."


def show_messages(messages: list) -> None:
    """Print exactly what we're about to send, so nothing is hidden."""
    print("    >>> Sending this messages list to Ollama:")
    for m in messages:
        # Truncate long content in the printout only, for readability -
        # the FULL content is still what actually gets sent.
        preview = m["content"] if len(m["content"]) <= 100 else m["content"][:100] + "..."
        print(f"        [{m['role']}] {preview}")


def chat(messages: list) -> str:
    show_messages(messages)
    response = ollama.chat(model=MODEL, messages=messages)
    return response["message"]["content"]


def main():
    print(f"Model: {MODEL}\n")

    # ------------------------------------------------------------------
    # Phase 1: a real, growing conversation. Every turn is appended to
    # `messages` and NOTHING is ever removed. By the third turn, the
    # full history (system + 5 prior messages) goes out on every call.
    # ------------------------------------------------------------------
    print("=" * 70)
    print("PHASE 1: full history kept")
    print("=" * 70)

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    # --- Turn 1: state a fact -----------------------------------------
    fact_turn = {"role": "user", "content": "My favorite programming language is Python."}
    messages.append(fact_turn)
    fact_reply = chat(messages)
    messages.append({"role": "assistant", "content": fact_reply})
    print(f"\nUser: {fact_turn['content']}")
    print(f"AI: {fact_reply}\n")

    # --- Turn 2: a deliberately UNRELATED question ----------------------
    # Important: this question must not contain or invite the word
    # "Python" (or any language name) in a plausible answer. If it did,
    # the fact could "leak" back into context through THIS turn instead
    # of the one we're trying to isolate - and Phase 2 would look
    # successful for the wrong reason. "Staying organized" has no
    # natural connection to any specific language.
    filler_turn = {"role": "user", "content": "What's a good way to stay organized while coding on a big project?"}
    messages.append(filler_turn)
    filler_reply = chat(messages)
    messages.append({"role": "assistant", "content": filler_reply})
    print(f"\nUser: {filler_turn['content']}")
    print(f"AI: {filler_reply}\n")

    # --- Turn 3: ask the model to recall the fact -----------------------
    recall_turn = {"role": "user", "content": "What is my favorite programming language?"}
    messages.append(recall_turn)
    recall_reply = chat(messages)
    messages.append({"role": "assistant", "content": recall_reply})
    print(f"\nUser: {recall_turn['content']}")
    print(f"AI: {recall_reply}\n")

    print(">>> Phase 1 result: the fact-stating turn IS in the messages list")
    print(">>> sent above, so a correct answer here proves nothing on its own -")
    print(">>> it's exactly what we'd expect. The real test is Phase 2.\n")

    # ------------------------------------------------------------------
    # Phase 2: ask the SAME final question, but build a NEW messages
    # list from scratch that only contains the system prompt and the
    # unrelated filler exchange - the fact-stating turn and its reply
    # are never added at all.
    #
    # We build this explicitly (not by slicing the Phase 1 list) so
    # there's no risk of accidentally keeping a turn we meant to drop.
    # ------------------------------------------------------------------
    print("=" * 70)
    print("PHASE 2: fact-stating turn removed")
    print("=" * 70)

    trimmed_messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        filler_turn,
        {"role": "assistant", "content": filler_reply},
    ]

    follow_up = {"role": "user", "content": "What is my favorite programming language?"}
    trimmed_messages.append(follow_up)
    trimmed_reply = chat(trimmed_messages)
    print(f"\nUser: {follow_up['content']}")
    print(f"AI: {trimmed_reply}\n")

    # ------------------------------------------------------------------
    # Verdict - checked mechanically, not just eyeballed, so the
    # conclusion in the README isn't based on a guess either.
    # ------------------------------------------------------------------
    print("=" * 70)
    print("VERDICT")
    print("=" * 70)
    mentions_python = "python" in trimmed_reply.lower()
    if mentions_python:
        print(
            "Phase 2's reply still mentions Python. Since the fact-stating\n"
            "message is verifiably NOT in the list printed above, this is not\n"
            "real recall - it's a guess (Python is an extremely common answer\n"
            "for AI assistants to default to) or a coincidence. Compare the\n"
            "wording/confidence of this answer to Phase 1's - a genuine recall\n"
            "usually sounds certain ('you told me...'), a guess often hedges."
        )
    else:
        print(
            "Phase 2's reply does NOT mention Python - the model has no way\n"
            "to answer correctly, exactly as expected, because the fact\n"
            "genuinely is not present anywhere in the list sent to it."
        )

    print(
        "\nConclusion: 'memory' here is entirely the messages list our own\n"
        "code chooses to build and resend. Ollama's API never stores\n"
        "anything between calls - remove a message from the list and it is,\n"
        "as far as the model is concerned, a fact that never existed."
    )

    # Save the full transcript as JSON too, for pasting exact evidence
    # into the README without retyping anything by hand.
    record = {
        "model": MODEL,
        "phase_1_messages_sent_on_final_call": messages[:-1],  # excludes the reply appended after
        "phase_1_final_answer": recall_reply,
        "phase_2_messages_sent": trimmed_messages,
        "phase_2_final_answer": trimmed_reply,
    }
    with open("memory_investigation_result.json", "w", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print("\nFull transcript saved to memory_investigation_result.json")


if __name__ == "__main__":
    main()
