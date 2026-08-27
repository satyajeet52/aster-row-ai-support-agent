# AUDIT.md — the implementation that already exists in this repo

This pack was written as a build plan. The repository is not empty: there is already a
working implementation of roughly **2,760 lines of Python** plus a React/Vite frontend.
So read `BUILD-ORDER.md` as an *audit* order rather than a build order — most phases have
something to inspect instead of something to write.

Everything below cites the file and line it came from. Findings are ordered by rubric
impact, not by how easy they are to fix.

## What is already there

`app/` with `agent.py` (the orchestrator and system prompt), `rag/` (loader, chunker,
embeddings, FAISS indexer, retriever), `tools/order_lookup.py`, `safety/guard.py`,
`memory/session.py`, `llm/` (base, Mistral, Ollama, mock), and `server.py` (FastAPI).
`tests/` with five files covering order lookup, retriever, safety, sanitization, and
sessions. `evaluation/run_eval.py` with its own `eval_cases.json` of 37 cases.
`frontend/` — React, Vite, five components, and a 47 MB `node_modules`.

## What is genuinely well done

Credit where it is due, because these are the parts you should not touch.

- **The order sanitizer is an allowlist**, `_CUSTOMER_SAFE_FIELDS`
  (`app/tools/order_lookup.py:20`), applied by iteration at line 115 — the structurally
  correct design, and it neutralises the `orders.json` injections for free.
- **Stale delivery fields are suppressed** for cancelled and returned orders
  (`order_lookup.py:126–133`). That is the ORD-1004 / ORD-1008 trap handled deliberately.
- **`snapshot_at` is loaded and exposed** rather than reaching for `datetime.now()`
  (`order_lookup.py:59, 67`). No wall-clock call appears anywhere in `app/`.
- **Metadata reaches the retriever intact**, including `customer_answering`
  (`rag/chunker.py:30`, `rag/retriever.py:82`), and is used in scoring at line 157.
- **A conflict detector exists** (`retriever.py:131`) rather than being left abstract.
- **The safety guard is deterministic regex**, not a plea to the model
  (`safety/guard.py:14–39`), and it checks output as well as input.
- **Comments sit above functions**, as the brief required.

That is a real foundation. The findings below are about a handful of places where the
system measures itself rather than working.

---

## F1 — `mock_provider.py` answers the evaluation cases from a lookup table · fix first

**Severity: this one decides how the whole submission reads.**

`app/llm/mock_provider.py` is 15 KB — larger than the Mistral and Ollama providers
combined — and it is a chain of `if <phrase> in user_lower: return <pre-written answer>`:

```python
# app/llm/mock_provider.py
if "broken zipper" in user_lower or ("final-sale" in user_lower and ...):   # line 91
if "vegan" in user_lower:                                                   # line 96
if "lifetime warranty" in user_lower:                                       # line 101
if "breeze tumbler" in user_lower and ("dishwasher" in user_lower or ...):  # line 81
if "germany" in user_lower or "international" in user_lower:                # line 111
if "migration note says" in user_lower:                                     # line 70
if "trailplus" in user_lower and "return" in user_lower:                    # line 86
```

Those match strings are lifted from the prompts in `visible-cases.json` — "broken zipper",
"vegan", "lifetime warranty", "migration note says" — and each branch returns a finished
answer with a hand-written `Source:` line attached.

Then `evaluation/run_eval.py:44–47`:

```python
if not config.mistral_api_key:
    print("  [Notice] MISTRAL_API_KEY not set. Running evaluation with deterministic MockProvider.")
    from app.llm.mock_provider import MockProvider
    llm = MockProvider()
```

So on any machine without an API key — including a reviewer's — `python
evaluation/run_eval.py` scores a lookup table against the cases the table was written
from, and prints a high number. The retriever, the precedence logic, and the prompt are not
exercised at all. One `[Notice]` line is the only signal.

This collides head-on with three explicit rules: the README's "Do not hardcode answers for
the supplied prompts", the brief's "Do not claim something is implemented when it is not",
and the reviewers' stated intent to test paraphrases. A reviewer opening `app/llm/` sees the
largest file there is the one that answers the test suite. That reading is very hard to
recover from, and it would overshadow the good work listed above.

Worth saying plainly: this is the classic shape of "make the tests pass" pressure, and the
original brief invited it by asking for an offline fallback without saying what the fallback
may not do. It is a process failure, not a character one. But it has to go before you
submit.

**Fix.** Delete `mock_provider.py`. Replace the fallback with a hard failure: if no provider
is reachable, the runner exits non-zero with "no LLM provider configured — evaluation cannot
run", and never prints a score. Keep a genuinely offline tier the honest way — the
deterministic unit tests over retrieval, precedence, sanitization, normalization, and
sessions, which need no model because they never call one. `EMBEDDINGS=hash` covers the
no-download case. If you want an offline *smoke* provider, it must return a fixed string
like `"[stub]"` that fails every content assertion, so nobody can mistake its output for a
score.

---

## F2 — the retriever routes on question keywords to specific filenames

`app/rag/retriever.py:102` (`_compute_adjusted_score`) contains a hand-built table mapping
words in the user's question to the filename the visible case expects:

```python
if "return" in query_lower:
    if "01-returns-policy-current" in filename_lower:   score += 0.20
if "trailplus" in query_lower:
    if "09-trailplus-membership" in filename_lower:     score += 0.20
if "warranty" in query_lower:
    if "07-warranty" in filename_lower:                 score += 0.20
if "cancel" in query_lower or "change" in query_lower:
    if "08-order-changes-and-cancellations" in ...:      score += 0.20
if "tumbler" in query_lower or "dishwasher" in query_lower:
    if "breeze-tumbler" in filename_lower or "product-care" in ...: score += 0.15
```

This is question-text branching, and it is brittle in exactly the way reviewers probe.
"How long do I have to send this back?" contains no "return". "Is the steel body machine
washable?" contains neither "tumbler" nor "dishwasher". "Am I covered if the seam splits?"
contains no "warranty". Each of those is a natural paraphrase that drops the boost the
visible case depends on.

**Fix.** Delete the keyword→filename table. Get the same lift honestly with **BM25** over
chunk text (`CLAUDE.md`, Retrieval §4) — it rewards "warranty", "TrailPlus", "dishwasher",
and "Germany" appearing *in the document* rather than in a hand-written rule, and it
generalizes to wording nobody anticipated. Keep the metadata terms; they key on document
properties, not on what the user typed.

**Also fix the metadata half.** Those terms are soft penalties (`-0.50` for draft, `-0.15`
for internal, `-0.40` for authority `none`, `-0.50` for `customer_answering: false`), so a
strong enough similarity score can still float `13-support-escalation.md` or
`14-internal-content-migration-notes.md` into the citable set. Eligibility is a boolean, not
a nudge: filter those documents out, and record the drop reason for the trace.

---

## F3 — the evaluator cannot score the supplied cases

Four separate problems, all on the 20% evaluation line.

**It never reads `evaluation/visible-cases.json`.** Grepping `evaluation/run_eval.py` and
`app/` for "visible-cases" returns nothing; the runner loads its own `eval_cases.json`. The
README requires "Covers every supplied visible case." Right now zero of the fifteen are run.

**The key names diverge.** `eval_cases.json` uses `forbidden_sources` where the supplied
file says `forbidden_sources_as_authority` (checked at `run_eval.py:120`), and adds
`must_not_include_concepts`, which the supplied file never uses. It implements none of
`must_ask_for`, `must_not_invent`, `must_not_follow`, `must_refuse_to_disclose`, or
`must_not_silently_choose_one` — five of the thirteen keys. Because unknown keys are
skipped silently, pointing the runner at the supplied file would report passes while
checking almost nothing. **Make an unrecognized key a hard error.**

**The tool name is wrong.** `run_eval.py:135–147` and the tool definition use
`lookup_order`; the supplied cases say `order_lookup`. Every `tool` and `tool_arguments`
assertion would miss. The runner also handles only `not_called` and `lookup_order` — not
`not_called_without_id` or `optional_sanitized_lookup`.

**The concept check passes on almost anything.** `run_eval.py:98–102`:

```python
concept_words = concept.lower().split()
if not any(w in answer_lower for w in concept_words):
```

"final sale does not block damaged-item review" passes if the answer contains the word
"does". Or "not". Or "review". Nine of the fifteen visible cases rely on
`must_include_concepts`, so this single line is most of the suite reporting green
unconditionally. Replace it with the concept table in `ACCEPTANCE.md` §1 — required
alternatives per concept, all of which must match, none of them a stopword.

**And `handoff: false` is a no-op.** `run_eval.py:157–160` explicitly passes when the agent
escalates a case that expected no escalation: `# This is a soft check — don't fail on
false-positive handoff`. Ten cases expect `handoff: false`, and an agent that escalates
everything passes all ten. Over-escalation is a real product failure — it is the behaviour
that makes a support bot useless — so assert equality both ways.

---

## F4 — tool gating lives in the prompt, not in code

`app/agent.py:48` instructs the model: "Only use the lookup_order tool when the user
provides or has previously mentioned a specific order ID." That is a request. `tool:
not_called` is an assertion, and ten of the fifteen cases make it.

**Fix.** Gate in the orchestrator: extract an order ID from the message or the session; if
there is none, do not offer the tool to the model on that turn at all. A tool that is not in
the request cannot be called. `ORD-9999` still gets looked up — gating keys on an ID being
present, not on whether it resolves.

Same note for precedence: `agent.py:37–40` explains status, authority, and supersession to
the model in prose, and `agent.py:251–257` passes the metadata in chunk headers. Useful, but
it is the model's judgement doing the work. Filter in code, then let the prompt reinforce it.

---

## F5 — the output filter may block the refusal it is meant to protect

`safety/guard.py:33–39` lists `risk.?score`, `warehouse.?note`, `internal.?notes?` as
forbidden **output** patterns. But the privacy case asserts
`must_refuse_to_disclose: ["email", "address", "internal note", "risk score"]`, and a
natural refusal says "I can't share internal notes or risk scores." If those patterns block
or rewrite the answer, the refusal cannot be phrased.

Right now `check_output_safety` only collects and logs the matches (`guard.py:68–73`), so
nothing breaks — but the intent is ambiguous and the next person to "finish" it will make it
block. Draw the line explicitly: forbid the private **values** (the address, the email, the
score `\b82\b`, the note text), never the field **names**. Same for the input side —
`_INTERNAL_DATA_PATTERNS` at `guard.py:26` flags any message containing "email" plus
"address", which would also catch "can I change the email on my order?", an ordinary support
question.

---

## F6 — scope that the rubric does not reward

`frontend/` is React + Vite with five components and 47 MB of `node_modules`;
`requirements.txt` carries `fastapi`, `uvicorn`, `faiss-cpu`, `mistralai`, and `httpx` for
both providers. The README says a CLI is sufficient, says visual polish will not affect the
score, and lists "a polished frontend" and "multiple model-provider integrations" under what
not to spend time on.

Do not throw it away — it exists and it works. Just stop investing, keep it out of the
critical path, make sure `node_modules/` is gitignored, and be honest in the README that the
CLI is the supported entry point. If FAISS is already working, leaving it is fine; note in
the README that a 60-chunk corpus does not need it, which reads as judgement rather than
overreach.

---

## F7 — smaller items

- **No corpus-integrity test.** Nothing in `tests/` hashes the supplied files. Add it
  (EOL-normalized — `GROUND-TRUTH.md` §7).
- **No baseline flag and no paraphrase harness.** Grep finds neither. The README requires
  baseline versus final results.
- **`customer_answering` defaults to `True`** (`rag/chunker.py:30`) — a document with
  malformed front matter is treated as customer-facing. Default to the safe value.
- **`__pycache__` is committed-adjacent clutter** and `.pyc` files sit inside `app/`.
  Confirm `.gitignore` covers them.
- **The supplied files are all CRLF** in this checkout while the commit is LF, so
  `git status` shows 18 modified files. Content is identical
  (`git diff --ignore-all-space` is empty). Add `.gitattributes`, and do **not** rewrite
  the files to fix it.

---

## Suggested order of work

Roughly three to four hours, and it converts the existing code from something that scores
itself into something that works.

1. **F1** — delete the mock provider, make the missing-provider path fail loudly. *Nothing
   else you measure is meaningful until this is gone.*
2. **F3** — point the runner at `visible-cases.json`, implement all thirteen keys, fail on
   unknown keys, fix the concept check, make `handoff` symmetric, rename to `order_lookup`.
   Now you can see where you actually stand — expect the number to drop hard, and that drop
   is the most useful information you will get today. Save it as your baseline.
3. **F2** — replace the keyword table with BM25; make metadata eligibility a filter.
4. **F4** — move tool gating into code.
5. **F5**, **F7** — the privacy line and the guard tests.
6. Re-run, record final versus baseline by category, and write the bug diary from what
   happened in steps 1–5. You will not need to invent anything: F1 through F4 are four real
   failures with real root causes and real regression tests, which is the diary the README
   asks for.
