# Examples

Two genuine runs, one per model family, so you can compare like with like.
Nothing here is mocked or hand-edited. Each set is three files: the raw
trial records (one JSON object per line — feed them to `analyse.py` or
`visualise.py` yourself), the text panel from `uv run analyse.py <jsonl>`,
and the self-contained HTML report from `uv run visualise.py <jsonl>`
(download and open it — GitHub shows HTML as source rather than rendering
it).

## `gpt-5.6-family-2026-07-15.*`

1,440 trials across three OpenAI models (`gpt-5.6-luna`, `-terra`, `-sol`):
`numbers` and `characters` evals, 8 pairs × both orderings × three
preference cells × 5 repeats per model. Total API cost: $0.25.

Headline: uniformity. All three models — small, medium and large alike —
agreed with an expressed user preference 91% of the time on characters and
100% of the time on numbers. Stating a preference all but decides the
answer, regardless of tier.

## `claude-family-2026-07-16.*`

1,152 trials across four Anthropic models (`claude-fable-5`,
`claude-opus-4-8`, `claude-sonnet-5`, `claude-haiku-4-5`): same evals and
grid, 3 repeats per model. Total API cost: $0.92.

Headline: spread. `haiku` barely follows an expressed preference at all
(50–56%), `sonnet` is nearly GPT-like (85–100%), `fable` and `opus` sit
between — and position biases vary wildly by model (`haiku` picks the
first-listed number 88% of the time; `opus` leans second).

## Across both families

Every one of the seven models, both companies, picked Batman over Superman
and Samwise Gamgee over Frodo Baggins in every single no-preference trial.
The old "GPT models prefer bigger numbers" lean is still visible (strongest
in the smallest GPT model) but is no longer the whole story — `sol` takes
7 over 40 every time, and `opus` and `sonnet` disagree in opposite
directions on the same 31-vs-39 pair.

One footnote: the gpt-5.6 records predate a small change to
`Trial.timestamp` (it now records completion time; at the time of that run
it recorded build time), which is why that report's footer shows the whole
run "collected" in a single minute. The claude records carry true
completion times.
