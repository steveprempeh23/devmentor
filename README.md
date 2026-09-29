# DevMentor

## Description

DevMentor is a command-line conversational AI assistant that runs entirely
against a local Ollama model. It fuses three earlier building blocks —
a basic local LLM call, a prompt-driven assistant, and a chatbot with
conversation memory — into one small application with a defined
personality, multi-turn memory, reset/history/exit controls, and graceful
error handling.

No frameworks (LangChain, agents, RAG libraries, vector DBs) are used.
Everything here is plain Python talking to the `ollama` Python package.

## Features

- Chats with any installed local Ollama model (`llama3.2`, `qwen2.5`,
  `mistral`, `gemma2`, ...)
- Clear, rule-based system prompt that shapes tone, explanation style,
  and behaviour when unsure
- Full multi-turn conversation memory (the entire message list is resent
  every turn)
- `/reset` — clears history, keeps the system prompt
- `/history` — prints numbered user/assistant turns (never the system
  message)
- `/exit` — clean shutdown
- `/save` and `/load <file>` — persist and restore a conversation
  (Bonus 2 / 3)
- Model picker and personality-mode picker at startup (Bonus 1 / 5)
- Graceful handling of: Ollama not running, empty input, unknown/missing
  model
- Blunt context-length management (`trim_history`) once a conversation
  passes a configurable number of turns (Bonus 4, partial implementation)

## Architecture

```
 User
   |
   v
 main.py  (loop, commands, error handling)
   |            \
   v             \--> config.py   (model name, host, settings)
 messages[]                        \--> prompts.py  (system prompts)
 (conversation history,
  lives in this Python
  process only)
   |
   v
 ollama.chat(model, messages)   <-- Ollama HTTP API (localhost:11434)
   |
   v
 Local LLM (e.g. llama3.2)
   |
   v
 Response text --> printed to user, appended to messages[] as
                   {"role": "assistant", ...}
```

**Where the model lives:** entirely on your machine, served by the
Ollama daemon — no data leaves localhost.

**Where conversation state lives:** nowhere but the `messages` Python
list inside this process. Close the program and it's gone, unless you
`/save` it to disk first.

**What the API does:** `ollama.chat()` is a thin wrapper over a stateless
HTTP POST to Ollama's `/api/chat` endpoint. It has no idea this is turn
12 of a conversation — it only ever sees what's inside the `messages`
array of *this* request.

**What is sent on every request:** the system message plus every user
and assistant turn we've chosen to keep (subject to `trim_history`).
That resending is the entire mechanism behind "memory" — see the Memory
Investigation section below.

File responsibilities:

| File | Job |
|---|---|
| `config.py` | Model name, Ollama host, app settings |
| `prompts.py` | System prompt, personality modes, experiment prompts |
| `main.py` | Startup, main loop, commands, Ollama calls, error handling |
| `experiment.py` | Standalone script for the Part 7 prompt experiment |
| `memory_investigation.py` | Standalone script for the Part 8 memory investigation |
| `README.md` | This file |

## Installation

```bash
git clone <your-repo-url>
cd devmentor
python -m venv .venv && source .venv/bin/activate   # optional but recommended
pip install -r requirements.txt

# Make sure Ollama is installed and running, and you've pulled a model:
ollama pull llama3.2:1b
```

> **Note on model names:** Ollama model names include a tag (the part
> after the colon), and matching is exact — `ollama.chat(model="llama3.2")`
> looks for `llama3.2:latest` specifically, and 404s if you've only
> pulled a different tag (e.g. `llama3.2:1b`). Run `ollama list` and use
> exactly what it prints. `config.py`'s `DEFAULT_MODEL` is set to
> `llama3.2:1b` to match; edit it if your own tag differs. `main.py`'s
> model picker now queries `ollama.list()` directly at startup rather
> than relying on a static list, specifically to avoid this class of bug.

## Running the Application

```bash
python main.py
```

You'll be asked to pick a model and a personality mode (press Enter for
the defaults). Then chat normally. Type `/history`, `/reset`, `/save`,
`/load <filename>`, or `/exit` at any point.

Sample session:

```
1. Beginner Tutor
2. Senior Engineer
3. Code Reviewer
4. Socratic Teacher
============ DevMentor AI Assistant ============
Model: llama3.2   |   Commands: /reset  /history  /save  /load <file>  /exit
------------------------------------------------

You: What is an API?
AI: An API is a set of rules that lets two programs talk to each other...

You: Can you give an example?
AI: Sure — when a weather app asks a weather service for today's forecast,
    that request-and-response is happening through an API...
```

Notice the second question never repeats the word "API" — DevMentor
still understands the thread because the full history is resent each
turn.

## System Prompt Design

The default system prompt (`prompts.DEFAULT_SYSTEM_PROMPT`) defines,
explicitly:

- **Who the assistant is** — DevMentor, a programming tutor
- **Who it's talking to** — junior developers shaky on fundamentals
- **How it should explain things** — plain language first, short code
  second, analogies over academic definitions
- **How it should use examples** — short, runnable, capped in length
- **What it does when unsure** — says so, or asks one clarifying
  question instead of guessing

This isn't the starter sketch from the brief — it adds explicit
constraints (intro length, code length, default behaviour under
ambiguity) that the starter left vague, because vague rules are the ones
that get ignored (see the experiment below).

## Prompt Engineering Experiment

Run it yourself with:

```bash
python experiment.py
```

This asks all three prompts (A: Minimal, B: Detailed, C: Constrained —
defined in `prompts.py`) the same four questions and saves the full
transcript to `experiment_results_<timestamp>.json`.

Results below are from a real run against `llama3.2:1b`, saved in full in
`experiment_results_2026_09_29_131234.json`.

**Sample: "Show me an example."** (deliberately vague — no topic named)

- **Prompt A (Minimal)** picked its own topic with no acknowledgment of
  the ambiguity — jumped straight into a "Hello, World!" example.
- **Prompt B (Detailed)** also just picked a topic (variables) and ran
  with it, no clarifying question asked despite the ambiguity.
- **Prompt C (Constrained)** also picked a topic rather than asking a
  clarifying question, *despite* rule 4 explicitly saying to ask one
  under ambiguity — this rule was the least reliably followed of the
  five, across multiple runs.

**Sample: "Explain REST APIs."**

- **A** produced a long, dense list-heavy answer with no analogy —
  closest to a textbook definition.
- **B** consistently opened with a restaurant/ordering-food analogy
  before any technical content, matching its "use analogies" rule.
- **C** also used a plain-language-first structure and, notably, one run
  explicitly said *"I'm not sure what language you'd like me to use for
  code examples, but I'll use Python"* — directly enacting rule 3
  ("default to Python") in visible, checkable language.

1. **Which prompt was most useful, and why?**
   Prompt C, on balance — it was the only one that consistently led with
   a plain-language explanation before code (its rule 1), and the only
   one that visibly reasoned about its own rules out loud (the "I'll use
   Python" line). B came close and produced the most vivid analogies,
   but occasionally ran long on the intro despite the brief not asking
   for brevity from B.

2. **What differences did you see?**
   A was the most textbook-like — dense, list-heavy, no analogies. B was
   the most consistently analogy-driven (restaurant ordering, LEGO
   towers, ladders) but had no length discipline. C stuck closest to a
   short plain-language opener before code, though it wasn't perfectly
   consistent question to question.

3. **Did more instructions always help?**
   No. B has more instructions than A but isn't uniformly better — on
   "dependency injection," A's answer was arguably more structurally
   complete (benefits, common scenarios, summary) than B's single
   analogy-then-code-then-nothing-else structure. More rules helped
   where they were concrete (format, defaults) and did less where they
   were about *quality* in the abstract (B never explicitly said "be
   concise," so it wasn't).

4. **Which rules changed behaviour the most?**
   Rule 3 in Prompt C ("default to Python") — directly observable, model
   explicitly reasoned about it in at least one answer rather than just
   silently complying. Rule 1 ("explain before code") in C was the
   second most visible — C's structure was noticeably more consistent
   about ordering than A or B.

5. **What happened when a rule was vague?**
   The clearest case wasn't in the prompts themselves but in the *user
   question* — "Show me an example" gave no topic, and none of the three
   prompts (including C, despite its own explicit "ask a clarifying
   question under ambiguity" rule) actually asked what kind of example
   was wanted. This shows a limit worth being honest about: on a small
   1B-parameter local model, even an explicit, numbered rule about
   handling ambiguity isn't followed with full reliability — the rule
   biases behaviour, it doesn't guarantee it.

## Memory Investigation

Run it yourself with:

```bash
python memory_investigation.py
```

**Does the LLM actually "remember" the conversation?**

No. Ollama's `/api/chat` endpoint is stateless — each call is
independent. What looks like memory is entirely an illusion created by
our own application: `main.py` keeps every turn in the `messages` Python
list and resends the whole list on every call. The model only ever
"knows" what's inside the request it just received.

- **Application state** — the `messages` list is ordinary state living
  in this Python process. Nothing about it is special to the model;
  it's just data we chose to keep.
- **Message history** — every prior user and assistant turn we've
  appended to `messages`, in order.
- **The context you send on each request** — exactly this: system
  message + trimmed history + the new user turn. Nothing more, nothing
  less.

**Real run** against `llama3.2:1b` (full transcript in
`memory_investigation_result.json`). `memory_investigation.py` prints
the exact `messages` list sent on every call, so the "fact removed" claim
below is verified by inspection, not assumed.

*Phase 1 — full history kept:*
```
User: What is my favorite programming language?
AI: You mentioned Python earlier. Is there something specific you're
    working on in Python that you'd like help with?
```
Correct and confident — the fact-stating message is verifiably still in
the request.

*Phase 2 — the fact-stating message removed, confirmed by the printed
`messages` list (4 entries: system, an unrelated "staying organized"
exchange, and the new question — no mention of Python anywhere):*
```
User: What is my favorite programming language?
AI: I don't have personal preferences or opinions, but many people
    enjoy learning and working with Python due to its simplicity,
    readability, and versatility.
```
This still contains the word "Python," but the tone gives it away: it
opens by disclaiming any personal knowledge, then pivots to a generic
claim about Python's popularity in general — compare that to Phase 1's
direct, confident "you mentioned Python earlier." This isn't recall,
it's the model defaulting to "Python" as a statistically common answer
to "name a programming language," because that's genuinely the only
thing available to it once the actual fact is gone from context.

**Conclusion:** there's no hidden store inside the model holding onto
anything between calls. If a fact isn't in `messages`, it doesn't exist
for that call — at best the model can guess using generic priors from
its training data, which is visibly different from a real recall both
in confidence and in specificity.

## Bonus Notes

- **Bonus 1 (Model selection):** implemented — `choose_model()` in
  `main.py`.
- **Bonus 2 / 3 (Save / Load):** implemented — `/save` and `/load
  <filename>`, storing full JSON message lists (system prompt included,
  since that's required to restore the assistant's behaviour, not just
  its facts).
- **Bonus 4 (Context awareness):** A context window is the maximum
  number of tokens a model can attend to in a single call (prompt +
  completion combined). As a conversation grows, eventually the full
  history no longer fits — providers either truncate silently, error
  out, or (worse) push out the system prompt. Two mitigation strategies:
  1. **Sliding window** — keep only the last N turns (this repo's
     `trim_history` does a basic version of this).
  2. **Summarisation** — periodically replace older turns with a short
     model-generated summary message, preserving the gist at a fraction
     of the token cost.
- **Bonus 5 (Configurable personality):** implemented — `choose_personality()`
  offers Beginner Tutor, Senior Engineer, Code Reviewer, and Socratic
  Teacher modes, each with its own system prompt in `prompts.py`.

## Challenge Questions

1. **Why does the app send previous messages to the LLM?**
   Because the API itself has no memory between calls. If we don't
   resend prior turns, the model has no way to know they happened.

2. **Difference between system, user, and assistant messages?**
   `system` sets behaviour/persona and is invisible to the "conversation"
   proper; `user` is what the human typed; `assistant` is what the model
   previously replied. All three are replayed on each call so the model
   has full context of both its own prior answers and the instructions
   governing it.

3. **Why does the assistant "forget" after restarting Python?**
   Because `messages` only ever lived in this process's memory (RAM).
   Nothing was persisted to disk unless you explicitly ran `/save`.

4. **Is memory stored inside the LLM or inside your application?**
   Inside the application. The model itself is stateless between API
   calls; the illusion of memory is entirely a product of what our code
   chooses to resend.

5. **What happens when a conversation becomes extremely long? What is a
   context window?**
   See "Bonus 4" above — eventually the message list exceeds the
   model's context window (its maximum input+output token budget), and
   older content must be trimmed, summarised, or dropped, or the request
   fails outright.

6. **Why is "You are helpful." a weak system prompt? How would you
   improve it?**
   It gives no audience, no format, no behaviour under ambiguity, and no
   constraints — so the model falls back on generic defaults that vary
   run to run. Improve it by specifying: who the audience is, how
   answers should be structured (plain language first? code first?
   length limits?), and what to do when the request is unclear or the
   model is unsure — exactly what `DEFAULT_SYSTEM_PROMPT` does here.

7. **After the LLM replies, what should happen to `messages` before the
   next user turn, and why?**
   The assistant's reply must be appended to `messages` as
   `{"role": "assistant", "content": ...}` before the next call — that's
   what lets the model "see" its own previous answer and stay consistent
   with it on the following turn. `main.py` does this immediately after
   printing each reply.

## What I Learned

*(Fill in briefly after building/running: what surprised you about
statelessness, what broke first, what you'd change with more time.)*

---

## Front-page student details

| Field | Your details |
|---|---|
| Full name | Nana Owusu Achiaw Prempeh |
| Student ID | *(fill in)* |
| Programme | MSc Data Science and Analytics |
| Course code | STD701 |
| Assignment | Assignment 1 |
| Repository URL | *(fill in)* |
| Date submitted | *(fill in)* |
