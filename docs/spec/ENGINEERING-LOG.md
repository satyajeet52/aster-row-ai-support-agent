# ENGINEERING-LOG.md

Created in Phase 0. **Append as you work, not at the end.** The README's bug diary is
assembled from this file, and a retrospective reconstruction is how invented bugs get into
a submission. If you did not paste real output when it happened, do not write the entry.

Rules for this file: paste actual terminal output, not a description of it. Record failures
that you fixed *and* failures you decided not to fix. Record decisions you reversed —
"tried X, it did not work, here is why" is worth more to a reviewer than a clean narrative.

---

## Environment

Filled in by Phase 0; the detail lives in `ENVIRONMENT.md`.

- Python:
- LLM provider and model:
- Embedding backend:
- Anything that would not install:

---

## Phase gates

One row per gate. `BUILD-ORDER.md` names the command for each.

| Phase | Gate command | Result | Elapsed | Notes |
|---|---|---|---|---|
| P0 | `python scripts/probe_env.py` | | | |
| P1 | `pytest tests/test_corpus_integrity.py -q` | | | |
| P2 | `pytest tests/test_retrieval.py tests/test_precedence.py -q` | | | |
| P3 | one answer end to end + baseline saved | | | |
| P4 | `pytest tests/test_tool.py tests/test_privacy.py tests/test_session.py -q` | | | |
| P5 | `python -m evaluation.runner` + `pytest -q` | | | |
| P6 | `python -m app.cli --session verify` | | | |
| P7 | clean-clone walkthrough | | | |

---

## Bugs

Minimum three, each with real pasted output and a named regression test. At least one must
be something the visible cases did **not** point at — a failure you found by probing your
own system rather than by reading the fixture. That one is the entry a reviewer will read
most carefully, because it is the one that cannot be faked.

Copy this block per bug.

### BUG-00 — one-line summary

- **Found during:** phase / while doing what
- **Symptom:** what the agent actually did

- **Reproduction:**

  ```
  $ <exact command>
  <exact output — trimmed, not paraphrased>
  ```

- **Root cause:** the real mechanism, in the code, named by file and function. Not "the
  model hallucinated" — *why* was the model in a position to hallucinate? Which layer
  should have prevented it?
- **Fix:** what changed, and what you chose not to change.
- **Regression test:** `tests/test_x.py::test_y` — and how it fails if the fix is reverted.
- **Category:** retrieval / precedence / grounding / tool / privacy / session / injection /
  evaluator

---

## Decisions and tradeoffs

Anything a reviewer might otherwise read as an oversight. Format: decision, alternative
rejected, why. Candidates that will come up: numpy over FAISS; BM25 plus embeddings rather
than either alone; chunking by `##` rather than fixed windows; explicit supersession graph
rather than date comparison; enumerated handoff triggers rather than a confidence score;
field allowlist rather than blocklist; one provider rather than two.

---

## Cuts

Anything dropped for time, with the reason and what it would cost to add. This section
becomes the README's "known limitations" — an honest list here is worth more than an
implied claim of completeness.

---

## AI tool use

Required by README item 9. Which tools, what for, and **one concrete suggestion that was
wrong or incomplete** — the actual snippet, why it was wrong, what you did instead. Note it
the moment you catch one; by Phase 7 you will not remember the specifics, and a vague
answer here reads as a non-answer.
