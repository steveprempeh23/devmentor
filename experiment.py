#!/usr/bin/env python3
"""
experiment.py
-------------
Part 7 — Prompt Engineering Experiment.

Runs the same four questions against three different system prompts
(A: Minimal, B: Detailed, C: Constrained) and prints/saves the results
so they can be compared side by side. Run this once, then copy the
output into the README's "Prompt Engineering Experiment" section along
with your own observations.

Usage:
    python experiment.py
"""

import sys
import json
import datetime

import ollama
import config
import prompts

# Windows terminals can choke on non-ASCII characters small local models
# sometimes produce (em-dashes, math symbols, etc). Without this, such a
# character can crash the whole script mid-run with UnicodeEncodeError -
# this is exactly what happened partway through Prompt B during testing.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def run_prompt(system_prompt: str, question: str, model: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]
    response = ollama.chat(model=model, messages=messages)
    return response["message"]["content"]


def main():
    model = config.DEFAULT_MODEL
    results = {}

    for key, variant in prompts.EXPERIMENT_PROMPTS.items():
        print(f"\n=== Prompt {key} ({variant['label']}) ===")
        results[key] = {"label": variant["label"], "prompt": variant["prompt"], "answers": {}}
        for question in prompts.EXPERIMENT_QUESTIONS:
            print(f"\n-- Q: {question}")
            try:
                answer = run_prompt(variant["prompt"], question, model)
            except Exception as e:
                answer = f"[error: {e}]"
            print(answer)
            results[key]["answers"][question] = answer

    timestamp = datetime.datetime.now().strftime("%Y_%m_%d_%H%M%S")
    out_path = f"experiment_results_{timestamp}.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nSaved full results to {out_path}")


if __name__ == "__main__":
    main()
