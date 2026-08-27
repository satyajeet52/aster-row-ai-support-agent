# Spec pack — what this is and where it goes

This is your 34-section brief, re-engineered into something an agent can execute and a
reviewer can verify. Nine files: `CLAUDE.md` at the repository root, six more in
`agent-spec/`, and two working documents that are for you rather than for the repo.

## Read `AUDIT.md` first

The repository is **not empty**. It already holds about 2,760 lines of Python, five test
files, an evaluation runner with 37 of its own cases, and a React frontend with 47 MB of
`node_modules`. So the build plan in `BUILD-ORDER.md` is really an *audit* order: most
phases have something to inspect rather than something to write.

`AUDIT.md` walks that code with file and line citations. The short version: the sanitizer,
the stale-field suppression, the `snapshot_at` handling, and the metadata plumbing are
genuinely good. Three things need attention before this is submittable, and the first one
is urgent — `app/llm/mock_provider.py` answers the evaluation cases from a lookup table
keyed on phrases lifted from `visible-cases.json`, and `evaluation/run_eval.py` silently
falls back to it whenever `MISTRAL_API_KEY` is unset. On a reviewer's machine, the suite
would score a lookup table against the cases the table was written from.

## Install

`CLAUDE.md` goes at the repository root, where an agent loads it automatically every turn.
Everything else goes in `agent-spec/` — that is the path the documents reference in each
other, so keep the folder name.

```bash
cd /path/to/ai-agent-intern-test
mkdir -p agent-spec
cp /path/to/spec-pack/CLAUDE.md .
cp /path/to/spec-pack/{GROUND-TRUTH,BUILD-ORDER,ACCEPTANCE,AUDIT,ENGINEERING-LOG,DEMO-SCRIPT}.md agent-spec/
```

`00-KICKOFF-PROMPT.md` and `PROMPT-CRITIQUE.md` are for you, not the repo. Leaving the
critique out of the submission is deliberate — a reviewer is grading the agent, not the
brief that produced it. `AUDIT.md` is a judgement call: it is useful to an agent working on
the code, and it is also a list of your own weak points. Delete it before you push if you
would rather not ship it.

Then open a fresh agent session at the repo root and paste the block from
`00-KICKOFF-PROMPT.md`. Read its last section first; it asks you to make one decision
(which LLM backend) that Phase 0 would otherwise stop and ask about.

## The files

| File | Where | What it does |
|---|---|---|
| `CLAUDE.md` | repo root | The rules, always in context. Mission, rubric weights as the tie-breaker, non-negotiables, stop-and-report protocol, pinned stack, retrieval and precedence rules, citation format, the order-tool allowlist, sessions, safety, handoff triggers, observability fields, code conventions. |
| `AUDIT.md` | `agent-spec/` | The existing implementation, reviewed with file and line citations. Seven findings ordered by rubric impact, what is already right, and a three-to-four-hour order of work. |
| `00-KICKOFF-PROMPT.md` | yours | The first message. One page, then the agent works from the phase gates. |
| `BUILD-ORDER.md` | `agent-spec/` | Eight phases, 7h20 of budget, each with an exit gate that is a command rather than a feeling. Includes the cut order for when you fall behind. |
| `ACCEPTANCE.md` | `agent-spec/` | Definition of done. All thirteen assertion keys, text normalization, the reporting contract, three anti-hardcoding enforcements, the clean-clone walkthrough, and a final gate table. |
| `GROUND-TRUTH.md` | `agent-spec/` | Verified facts read out of the supplied files: the 14-document metadata table, the deterministic precedence rules, the one genuine conflict, all 12 orders with their traps, the three injection sites, the private values. For writing tests — application code must never reference it. |
| `ENGINEERING-LOG.md` | `agent-spec/` | Append-as-you-go log. Phase gate results, bugs with pasted output, decisions, cuts, AI-tool notes. The README's bug diary is assembled from this. |
| `DEMO-SCRIPT.md` | `agent-spec/` | Shot list for the required recording — a single 3:40 take with exact prompts and what must be visible in each frame. |
| `PROMPT-CRITIQUE.md` | yours | Why the draft changed: three rubric conflicts, six enforceability failures, fourteen missed requirements, two impossible asks, and a table mapping every original section to its new home. |

## The four changes that matter most

**Your brief would have spent hours on work the rubric does not reward.** Section 23 asked
for a polished React/Vite/Tailwind interface across ~1,200 words. The repository README
says a CLI is sufficient, says visual polish will not affect the score, and lists "a
polished frontend" under what not to spend time on. Same for the two-provider abstraction.
Both are now capped: 45 minutes for the interface, one provider behind a small seam. On a
6–8 hour clock that is roughly two hours redirected into the 25% and 20% rubric lines.

**The bug diary was structured to invite fiction.** Asking at the end for "at least 3 REAL
bugs" while also saying "do not invent fake bugs" is asking an agent to remember something
it never recorded. The log is now created in Phase 0 and appended at the moment each failure
happens, with real output pasted in, and Phase 5's gate refuses to pass without three
entries.

**The baseline was a point in time, so the improvement was unfalsifiable.** It is now a
flag — `ASTER_BASELINE=1` disables precedence, metadata filtering, conflict detection, tool
gating, and abstention while leaving the privacy sanitizer on. Both numbers come from the
same command on the same cases. The privacy exception is not a detail: never ship a code
path that can leak a customer's address, not even behind a flag, not even to make a metric
look better.

**Reading the supplied files changed the design.** Precedence needs no heuristic — doc 01
declares `supersedes: RET-2024-01` and doc 14 carries `customer_answering: false`, so the
rules are exact. There is exactly one genuine conflict (product care vs the tumbler product
card, both active, both official, same dates). Only 4 of the 15 visible cases require a tool
call and ten expect none, so an eager tool-caller fails the majority of the suite. `handoff`
is `true` on a question the agent can fully answer and `false` on the injection case, so a
confidence threshold gets both wrong. There are thirteen assertion keys, not twelve — the
easily-missed one appears on a single case. Two injections hide in `orders.json` internal
notes that your brief never mentioned, and a field allowlist kills them structurally. And
doc 09 words the TrailPlus window as "45-calendar-day" while the case asserts "45 calendar
days", so quoting the correct document verbatim fails the check.

## Two honest notes

The stack is pinned for install reliability, not because it is the only defensible choice.
Phase 0 probes the machine and the agent may deviate with a one-line justification in the
log. Where the existing code already made a different call — FAISS, FastAPI — `AUDIT.md`
says leave it rather than churn it.

`GROUND-TRUTH.md` was written by reading every supplied file directly, then re-verified
against the repository by script. That pass caught three errors in my own first draft, all
corrected and listed in its §8. The supplied files were not modified — they were opened
read-only, and `git diff --ignore-all-space` across all of them is empty.
