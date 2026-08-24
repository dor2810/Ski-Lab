# Ski Lab — Claude Project Setup Guide

---

## Step 1 — Custom instructions

Open `PROJECT_INSTRUCTIONS.md`, copy the fenced block, paste it into the Project's custom instructions field.

**This is the highest-value item in the whole package.** The documents describe *what* was built; the instructions encode *how we worked* — the norms that caught ten real bugs. Without them a fresh chat will write plausible code and confidently tell you it works.

---

## Step 2 — Upload files

### Upload these (in priority order)

| File | Why |
|---|---|
| **PROJECT_STATE.md** | The single most important upload. Current status, architecture, decisions, bugs, gaps. Supersedes the older handoff doc — don't upload that one, it's stale. |
| **ski_resort_database_seed.xlsx** | The 30-resort dataset. Real data, actively used. |
| **transfer_options.xlsx** | 56 transfer options across 26 pairs. |
| **MAC_SETUP_RUNBOOK.md** | Step-by-step first-run guide with predicted failure modes. |
| **ski-trip-optimizer-blueprint.md** | The original vision doc. Still the reference for long-term direction. |
| **project-structure.md** | Target architecture and rationale. |
| **date-range-search-design.md** | Design for the flexible-dates mode. |
| **transfer-subsystem-design.md** | Design for the transfer subsystem. |
| **ski-lab-api-keys-guide.md** | Which API keys to get. ⚠️ Contains the now-obsolete Amadeus recommendation — the guide itself flags this. |

### Don't upload

- **`ski-trip-optimizer.zip`** — Project knowledge doesn't accept archives.
- **`ski-lab-project-handoff.md`** — superseded by PROJECT_STATE.md. Two conflicting status docs is worse than one.
- **`SkiTripOptimizer.jsx`, `ski-lab-brand-sheet.html`** — optional; only if you're doing frontend work.

### A likely snag

Claude Projects documents PDF, DOCX, CSV, TXT, HTML, ODT, RTF, EPUB, JSON and XLSX as supported. **`.md` isn't explicitly on that list.** It often works, but if an upload is rejected, rename the file to `.txt` — the content is identical and nothing is lost.

### The code itself

Source files can't go in Project knowledge (`.py` isn't supported, and there'd be ~40 of them). **The code belongs in git**, not a knowledge base. Once the repo exists, use Claude Code from the repo directory — it reads files directly, which is far better than uploaded snapshots that go stale the moment you edit anything.

Until then, PROJECT_STATE.md's architecture section is enough for a chat to reason about the code, and you can paste specific files when needed.

---

## Step 3 — Chat structure

Projects let you run several chats sharing the same knowledge. Suggested split — **create them as you need them**, not all at once:

**1. "First run — getting it working"** ← start here
Working through MAC_SETUP_RUNBOOK.md. Expect tracebacks from the auth and search tests; paste them in and fix. This is the highest-value chat right now and should be short-lived — once the code runs, its job is done.

**2. "Backend / engine"**
Ongoing: `routes/trips.py`, wiring live flight pricing into date search, the accommodation adapter, closing the airport-consistency gap.

**3. "Data research"**
Genuinely separate work: the remaining 20 transfer pairs, verifying 13 resorts' terrain data, ski pass season bands per resort. Doesn't need code context, and keeping it apart stops research from cluttering engineering threads.

**4. "Frontend"**
Only once the API actually runs. The real Next.js app replacing the prototype.

**5. "Business / strategy"**
Affiliate verification, pricing model, positioning. Distinct enough to deserve its own space.

**Why split at all:** each chat keeps its own history, so a long debugging session doesn't bury design context. They all share the Project files, so nothing needs re-explaining.

**Practical tip:** start a fresh chat when the topic genuinely changes, not when the current one gets long. Long focused chats are fine; mixed-topic chats are the problem.

---

## Step 4 — First message in a new chat

You shouldn't need much, but this works well:

> Read PROJECT_STATE.md before we start. I want to work on [X] today. Flag anything in what I'm asking that conflicts with the plan or piles onto the unverified pile.

That last clause matters — it's the norm that repeatedly stopped this project from stacking untested code on untested code.

---

## Step 5 — Keeping it current

PROJECT_STATE.md will go stale. The verification ledger in §1 especially — the moment the auth tests actually run, that table is wrong.

**Suggestion:** after any session that changes what's verified, ask the chat to produce an updated PROJECT_STATE.md and re-upload it, replacing the old one. Cheap, and it stops the knowledge base drifting from reality — which is the failure mode that makes a Project actively worse than no Project.

---

## What I'd do tonight, concretely

1. Create the Project, paste the custom instructions
2. Upload PROJECT_STATE.md + the two xlsx files + MAC_SETUP_RUNBOOK.md (the rest can follow)
3. Start chat #1, work through the runbook
4. When the tests run: ask for an updated PROJECT_STATE.md and re-upload

The remaining design docs are useful but not urgent — they matter when you resume feature work, not tonight.
