# CLAUDE.md

Notes to a future session picking this up cold. The deep context lives in
the local `ant`/`ait` databases (gitignored) — this file tells you they
exist and what's load-bearing. Read this, then go read those.

## First moves, every session

```sh
ant foundation        # the project's constitution (llmb-AkRXV) — read it before design calls
ant recent --limit 5  # what was decided lately
ait ready             # unblocked work, if any
ait log --last 3      # what past sessions shipped and flushed
```

## What this is

A small, deliberately boring instrument that measures LLM preference biases
(sycophancy, position effects, odder tendencies) with repeated forced-choice
A/B prompts. Broad-brush tendencies for busy researchers — not a benchmark,
not a platform, not science. If a change makes it look impressive rather
than simple, it's the wrong change.

## Load-bearing contracts (violating these broke attempt one)

- **`records.Trial` is the contract.** Ground truth (options, ordering,
  condition, stated preference) is recorded at generation time. Analysis
  reads trial records ONLY — never re-parse prompt text to recover what was
  asked. `Trial.timestamp` is completion time (the runner overwrites the
  build-time default when the response lands).
- **`evals/` convention:** each module defines `pairs(n)` yielding up to n
  `(option, option)` string tuples; discovery is automatic from the
  directory. This becomes a public contract once the phase-2 generator
  ships — don't change the signature casually.
- **Single stats brain:** `analyse.summarise()` computes numbers,
  `analyse.tendency_sentences()` makes the words; the text panel and
  `visualise.py`'s HTML are two renderers of the same `GroupSummary`.
  Nothing else may derive stats from trials. (Report ADR: ant `llmb-mjBCN`.)
- **Two doors, one room:** `visualise.py` is the standalone renderer;
  `main.py --html` imports `visualise.write_report`. No duplicated logic.
- **Output speaks in tendency sentences first**, numbers in parentheses.
  Threshold: only claim a tendency beyond 60/40 with ≥10 decided answers;
  otherwise say "not enough to call". Honesty over drama.
- **Free-text responses, forgiving matcher.** Structured outputs on the
  measurement path were rejected (constrained decoding changes what's
  measured; refusals are signal). See ant `llmb-VYQvH` for all rejected
  approaches and their reopening conditions before proposing "improvements".

## Conventions

- Python 3.11+, `uv` for everything (`uv run`, `uv sync`, `uv run pytest`).
- The matcher (`normalise`/`classify`) has the project's ONLY unit tests —
  a deliberate decision, not an omission. Don't add test scaffolding
  elsewhere; verify by running the tool.
- The default branch is `master`, deliberately. Never rename it.
- `.env` is the owner's file — never create, read, or print it. Keys load
  in-program via python-dotenv.
- `trials_*.jsonl` / `trials_*.html` are gitignored run artefacts. A
  1,440-trial reference dataset (`trials_bigrun.jsonl`, July 2026, three
  gpt-5.6 models) lives locally — see ant `llmb-XKtxA` for its headlines.
- The owner runs all git write commands themselves. Hand over the exact
  commands; never commit, push, or branch.
- British English in docs and output. No real names in durable artefacts.
- moat runs show 5 expected reds (4 org-level accepted risks + a per-repo
  branch-lock decision, ant `llmb-Ed6UZ`). That's steady state, not TODO.

## Sharp edges

- A safety hook screens Bash commands and can false-positive on substrings
  inside quoted prose (e.g. a dotenv filename, or "uv" next to
  package-management words in an `ant`/`ait` note). If blocked: stop,
  surface it, reword the prose — never work around the hook's intent, and
  ask the owner when unsure it's a false positive.
- Fresh runs cost real money. Build the trial grid and check the printed
  count before spending; re-render old JSONLs for free instead where
  possible.

## Where things stand (July 2026)

Phase 1 (core instrument) and the HTML report epic are complete and live at
github.com/UoGSoE/llm-biases. The open item is the phase-2 stretch epic
(`llmb-UkLWZ.2`): LLM-assisted eval authoring — deliberately sketched, not
broken down. Read ant `llmb-sYVTv` before designing it.
