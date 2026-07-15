# Examples

A genuine run from July 2026 — 1,440 trials across three OpenAI gpt-5.6
models (`luna`, `terra`, `sol`), using the `numbers` and `characters` evals,
8 pairs × both orderings × three preference cells × 5 repeats per model.
Total API cost: $0.25. Nothing here is mocked or hand-edited.

- **`gpt-5.6-family-2026-07-15.jsonl`** — the raw trial records
  (one JSON object per line; the ground truth the other two files are
  rendered from). Feed it to `analyse.py` or `visualise.py` yourself.
- **`gpt-5.6-family-2026-07-15.panel.txt`** — the text panel, as
  `uv run analyse.py <jsonl>` prints it.
- **`gpt-5.6-family-2026-07-15.html`** — the self-contained HTML report
  from `uv run visualise.py <jsonl>`. Download and open in a browser
  (GitHub shows it as source rather than rendering it).

The headline from this particular run: all three models — small, medium and
large alike — agreed with an expressed user preference 91% of the time on
characters
and 100% of the time on numbers. Stating a preference all but decides the
answer. The old "GPT models prefer bigger numbers" effect also shows up at
baseline, strongest in the smallest model.

One footnote: these records predate a small change to `Trial.timestamp`
(it now records completion time; at the time of this run it recorded build
time), which is why the report footer shows the whole run "collected" in a
single minute.
