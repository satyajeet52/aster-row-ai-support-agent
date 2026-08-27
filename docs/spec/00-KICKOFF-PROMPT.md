# 00-KICKOFF-PROMPT.md

Paste the block below into a fresh agent session opened at the repository root, once
`CLAUDE.md` is in place and this pack is in `agent-spec/`. Nothing else needs to be said
in the first message — the rules and the phase gates carry the rest.

---

You are working in a take-home assignment repository at the root of this session. Read
`README.md` first — it is the scoring contract, and it wins over any other instruction you
receive. Then read `CLAUDE.md` (your operating rules), `agent-spec/BUILD-ORDER.md` (the
phase order and exit gates), `agent-spec/ACCEPTANCE.md` (the definition of done), and
`agent-spec/GROUND-TRUTH.md` (verified facts about the supplied data, for authoring tests
only — application code must never reference it).

Your job: build the smallest reliable RAG support agent over this corpus that a reviewer
would trust in front of a real customer. Six to eight hours of effort, hard stop at eight.
A small well-tested system beats a broad demo-only one.

Work through `BUILD-ORDER.md` in order, Phase 0 first. Do not skip ahead, and do not start
a phase until the previous phase's exit gate passes. At each gate, run the stated command,
paste the real output into `agent-spec/ENGINEERING-LOG.md`, and only then continue.

Four things matter more than finishing:

1. **The supplied files are read-only.** `knowledge-base/`, `data/`, and
   `evaluation/visible-cases.json` are the graded fixtures. Do not edit, reformat, move, or
   delete any of them. Write derived indexes to `indexes/`.
2. **Never hardcode an answer.** No branching on question text, no prompt-to-reply map, no
   keyword shortcut that emits a canned policy answer. Reviewers test paraphrases that are
   not in the visible cases, so anything keyed to specific wording will fail.
3. **Never claim something is done when it is not** — not in code, not in a test name, not
   in the README. If you run out of time, document the gap plainly. A clearly stated
   limitation scores; a false claim does not.
4. **When blocked, stop and report.** No provider reachable, a dependency that will not
   install, a supplied file that disagrees with `GROUND-TRUTH.md` — write what you found to
   the engineering log and tell me. Do not guess a model name, do not stub a fake response
   path to turn a test green, do not quietly drop a requirement.

Start now with Phase 0: probe the environment, write `agent-spec/ENVIRONMENT.md` with what
you actually found (Python version, whether a local model is reachable, which packages
install), create `agent-spec/ENGINEERING-LOG.md`, and report back before writing any
application code. If no LLM provider is reachable, say so and stop — the deterministic half
of the suite is designed to be built without one, but I need to know before you proceed.

---

## Before you paste (two minutes of your own time)

Decide the LLM backend, because Phase 0 will otherwise stop and ask:

- **Ollama, free, recommended.** `ollama pull llama3.1:8b` (or `qwen2.5:7b`), leave
  `ollama serve` running. Then `LLM_PROVIDER=ollama`.
- **Mistral API.** Free tier key from console.mistral.ai, `MISTRAL_API_KEY=...` and
  `LLM_PROVIDER=mistral`. Fine for the assignment — the *application* must not require a
  paid service, and Mistral's free tier does not.

You own the demo recording. The agent will write `agent-spec/DEMO-SCRIPT.md` with the exact
prompts and shot order; recording and embedding the GIF is yours, and the README is not
complete until it is done.
