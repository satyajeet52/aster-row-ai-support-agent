# DEMO-SCRIPT.md — shot list for the README recording

The assignment requires a 2–4 minute GIF or video embedded in the README showing five
specific things. **An agent cannot operate a screen recorder — this one is yours.** The
script below is written so the recording is a single unbroken take of about 3:40, with no
editing and nothing to narrate from memory.

Do this at the very end, after `ACCEPTANCE.md` §5 passes. Recording a demo of a system you
are still changing means recording it twice.

## Setup

- Terminal at ~110×32, font large enough to survive GIF compression. Light or dark, but
  raise the contrast.
- Fresh shell, venv active, index built, provider running. Clear the scrollback.
- `--debug` **off** for the customer-facing shots. A reviewer wants to see what a customer
  sees; the trace gets its own moment in shot 5.
- Type at a readable pace. Do not paste — a reviewer watching text appear knows it is live.
- One take. A stumble is fine; a re-cut that hides a failure is not.

## The take

**0:00–0:10 — Frame it.** Show the repo root, `ls`. No talking head needed. If your tool
supports a title card: "Aster & Row support agent — CLI".

**0:10–0:50 — Knowledge-base answer with citations.**

```
python -m app.cli --session demo
```

Ask:

> How long do I have to return something I bought?

What must be visible on screen: **30 calendar days**, a citation naming
`01-returns-policy-current.md` and its heading, and no mention of 45 days or a free return
label. Pause two seconds on the citation line — this single frame is the retrieval and
precedence rubric lines (45% combined) in one image.

**0:50–1:25 — Order lookup.** Same session:

> Where is ORD-1007?

Must be visible: status shipped, carrier UPS, and the estimate as **August 22, 2026** in
long form. Nothing else. No email, no address, no internal note. Let it sit for a beat —
what is *absent* here is the privacy line, and absence needs a moment to register.

**1:25–2:05 — Multi-turn.** Same session, two turns:

> Do you ship internationally?

then

> What about Canada?

The second answer must be Canada-specific without the word Canada being repeated back at
it from a fresh retrieval — that is the context carry. If your CLI prints the resolved
context (`order: ORD-1007 · topic: international-shipping`), this is the shot where it
earns its place.

**2:05–2:45 — Refusing to guess, and the handoff.** Pick one; if the clock allows, both.

The conflict, which is the more interesting shot:

> Can I put the Breeze Tumbler in the dishwasher?

Must be visible: both `11-product-care.md` and `12-breeze-tumbler-product-card.md` cited,
an explicit statement that current official sources disagree, the safe interim
recommendation, and `handoff: true`.

Or the privacy refusal:

> What's the email address on ORD-1007?

Must be visible: a clean refusal, no address, no risk score, handoff.

**2:45–3:30 — Evaluation suite.**

```
python -m evaluation.runner
```

Let it run to completion in frame. What must land: per-case lines, the per-category
breakdown, and the totals. Then one command showing the baseline delta — if your runner
prints a comparison, use it; otherwise `head` the two result files side by side.

**3:30–3:40 — Close.** `python -m app.cli --session demo --debug` and one short question,
so the trace is visible for a few seconds. Then stop the recording.

## Producing the file

GitHub does not reliably play uploaded video inline. Either embed a GIF, or upload the MP4
and embed a clickable thumbnail that links to it.

```bash
# 3-4 min at 10fps, 900px wide — keep it under ~10 MB or GitHub will be slow to load it
ffmpeg -i demo.mov -vf "fps=10,scale=900:-1:flags=lanczos,split[a][b];[a]palettegen[p];[b][p]paletteuse" -loop 0 docs/demo.gif
```

In the README:

```markdown
![Agent demo](docs/demo.gif)
```

## Before you call it done

- [ ] All five required items are on screen, in order, in one take.
- [ ] No customer email, address, internal note, or risk score appears in any frame —
      including anything left in the scrollback.
- [ ] No API key, `.env` content, or shell history with a key is visible.
- [ ] The GIF is embedded and renders on the GitHub web view, not just locally.
- [ ] The `TODO: embed demo GIF` placeholder is gone from the README.
