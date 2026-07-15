"""Render a trials JSONL as a single self-contained HTML report.

Design decisions (recorded in the project notebook): stats come only from
analyse.summarise() - nothing here re-derives numbers from trial records;
the file is fully self-contained (inline CSS, inline SVG, no external
requests, system-font fallback); tendency sentences are the headline and
charts are supporting detail; every chart is followed by a visible table.
Styling follows the University of Glasgow design system tokens.
"""

import argparse
import html
from dataclasses import dataclass

from analyse import GroupSummary, group_trials, load_trials, summarise, tendency_sentences
from records import Trial

# University of Glasgow design-system tokens (design.gla.ac.uk)
UOFG_BLUE = "#011451"       # deepest navy: header, footer, headings
UOFG_DARK_BLUE = "#005398"  # everyday blue: bars, accents
TINT_40 = "#99A1B9"
TINT_20 = "#CCD0DC"         # bar tracks
TINT_10 = "#E6E7EE"         # section backgrounds
TEXT = "#323232"
MUTED = "#757575"
ERROR_RED = "#D4351C"

FONT_STACK = '"Noto Sans", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif'

CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: {FONT_STACK}; color: {TEXT}; line-height: 1.5; font-size: 1rem; }}
header, footer {{ background: {UOFG_BLUE}; color: #fff; padding: 1.5rem; }}
header h1 {{ font-size: 1.5rem; font-weight: 600; }}
header p, footer p {{ font-size: 0.875rem; color: {TINT_20}; margin-top: 0.25rem; }}
main {{ max-width: 60rem; margin: 0 auto; padding: 1.5rem; }}
section.eval {{ margin-bottom: 2.5rem; }}
h2 {{ color: {UOFG_BLUE}; font-size: 1.25rem; margin: 1.5rem 0 0.75rem; }}
h3 {{ font-size: 1rem; font-weight: 600; margin: 1rem 0 0.5rem; }}
.tendencies {{ background: {TINT_10}; border-left: 4px solid {UOFG_DARK_BLUE}; padding: 0.75rem 1rem; margin-bottom: 0.75rem; }}
.tendencies p {{ margin: 0.25rem 0; }}
.tendencies .counts {{ color: {MUTED}; font-size: 0.875rem; }}
.errors {{ color: {ERROR_RED}; font-weight: 600; }}
figure {{ margin: 1.25rem 0; }}
figcaption {{ font-weight: 600; margin-bottom: 0.5rem; }}
svg.chart {{ width: 100%; height: auto; max-width: 42rem; display: block; }}
table {{ border-collapse: collapse; margin: 0.5rem 0 1rem; font-size: 0.875rem; }}
th, td {{ text-align: left; padding: 0.375rem 0.75rem; border-bottom: 1px solid {TINT_20}; }}
th {{ color: {UOFG_BLUE}; }}
td.num {{ font-variant-numeric: tabular-nums; }}
footer {{ margin-top: 2.5rem; }}
footer dl {{ display: grid; grid-template-columns: max-content 1fr; gap: 0.25rem 1rem; font-size: 0.875rem; }}
footer dt {{ color: {TINT_40}; }}
"""


@dataclass
class RunMeta:
    models: list[str]
    evals: list[str]
    trials: int
    errors: int
    first_seen: str
    last_seen: str
    known_cost: float
    costed_trials: int


def run_meta(trials: list[Trial]) -> RunMeta:
    costed = [t.cost for t in trials if t.cost is not None]
    stamps = sorted(t.timestamp for t in trials)
    return RunMeta(
        models=sorted({t.model for t in trials}),
        evals=sorted({t.eval_name for t in trials}),
        trials=len(trials),
        errors=sum(1 for t in trials if t.error),
        first_seen=stamps[0][:16].replace("T", " ") if stamps else "",
        last_seen=stamps[-1][:16].replace("T", " ") if stamps else "",
        known_cost=sum(costed),
        costed_trials=len(costed),
    )


def bar_chart(chart_id: str, rows: list[tuple[str, float | None, int]]) -> str:
    """Horizontal SVG bars, one per model, with a dashed 50% neutral line.
    rows: (label, rate 0..1 or None when below threshold, decided n).
    """
    label_w, bar_w, row_h, pad_top, pad_bottom = 230, 320, 34, 8, 28
    width = 660
    height = pad_top + len(rows) * row_h + pad_bottom
    mid_x = label_w + bar_w / 2

    parts = []
    for i, (label, rate, n) in enumerate(rows):
        y = pad_top + i * row_h
        parts.append(
            f'<text x="{label_w - 10}" y="{y + row_h / 2}" text-anchor="end" '
            f'dominant-baseline="middle" font-size="14">{html.escape(label)}</text>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y + 8}" width="{bar_w}" height="18" '
            f'fill="{TINT_20}" rx="3"/>'
        )
        if rate is not None:
            parts.append(
                f'<rect x="{label_w}" y="{y + 8}" width="{bar_w * rate:.1f}" height="18" '
                f'fill="{UOFG_DARK_BLUE}" rx="3"/>'
            )
            parts.append(
                f'<text x="{label_w + bar_w + 8}" y="{y + row_h / 2}" '
                f'dominant-baseline="middle" font-size="14">'
                f"{round(rate * 100)}% (n={n})</text>"
            )
        else:
            parts.append(
                f'<text x="{label_w + 8}" y="{y + row_h / 2}" '
                f'dominant-baseline="middle" font-size="13" fill="{MUTED}">'
                f"not enough data (n={n})</text>"
            )

    line_bottom = pad_top + len(rows) * row_h + 4
    parts.append(
        f'<line x1="{mid_x}" y1="{pad_top - 2}" x2="{mid_x}" y2="{line_bottom}" '
        f'stroke="{MUTED}" stroke-dasharray="4 3"/>'
    )
    parts.append(
        f'<text x="{mid_x}" y="{line_bottom + 16}" text-anchor="middle" '
        f'font-size="12" fill="{MUTED}">50% (neutral)</text>'
    )

    return (
        f'<svg class="chart" role="img" aria-labelledby="{chart_id}-title" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<title id="{chart_id}-title">Bar chart with a dashed line marking the 50% neutral point</title>'
        f'<g fill="{TEXT}">{"".join(parts)}</g></svg>'
    )


def chart_table(headers: list[str], rows: list[list[str]]) -> str:
    head = "".join(f"<th scope=\"col\">{html.escape(h)}</th>" for h in headers)
    body = "".join(
        "<tr>" + "".join(
            f'<td class="num">{html.escape(cell)}</td>' for cell in row
        ) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def rate_cell(rate: float | None) -> str:
    return f"{round(rate * 100)}%" if rate is not None else "not enough data"


def eval_section(eval_name: str, summaries: list[GroupSummary]) -> str:
    blocks = [f"<section class=\"eval\"><h2>Eval: {html.escape(eval_name)}</h2>"]

    for gs in summaries:
        sentences = tendency_sentences(gs)
        counts_line = sentences[-1]
        lines = "".join(f"<p>{html.escape(s)}</p>" for s in sentences[:-1])
        error_note = (
            f' <span class="errors">{gs.errors} errored</span>' if gs.errors else ""
        )
        blocks.append(
            f"<h3>{html.escape(gs.model)}</h3>"
            f'<div class="tendencies">{lines}'
            f'<p class="counts">{html.escape(counts_line)}{error_note}</p></div>'
        )

    safe = eval_name.replace(" ", "-")
    blocks.append(
        f"<figure><figcaption>Agreement with a stated preference</figcaption>"
        + bar_chart(
            f"agree-{safe}",
            [(gs.model, gs.stated_agree_rate, gs.stated_decided_n) for gs in summaries],
        )
        + chart_table(
            ["Model", "Agreement rate", "Decided answers"],
            [[gs.model, rate_cell(gs.stated_agree_rate), str(gs.stated_decided_n)] for gs in summaries],
        )
        + "</figure>"
    )
    blocks.append(
        f"<figure><figcaption>First-option rate at baseline (position bias)</figcaption>"
        + bar_chart(
            f"first-{safe}",
            [(gs.model, gs.baseline_first_rate, gs.baseline_decided_n) for gs in summaries],
        )
        + chart_table(
            ["Model", "First-option rate", "Decided answers"],
            [[gs.model, rate_cell(gs.baseline_first_rate), str(gs.baseline_decided_n)] for gs in summaries],
        )
        + "</figure>"
    )
    blocks.append("</section>")
    return "".join(blocks)


def render_html(trials: list[Trial]) -> str:
    meta = run_meta(trials)
    groups = group_trials(trials)
    by_eval: dict[str, list[GroupSummary]] = {}
    for (model, eval_name), group in sorted(groups.items()):
        by_eval.setdefault(eval_name, []).append(summarise(group))

    sections = "".join(
        eval_section(eval_name, summaries) for eval_name, summaries in sorted(by_eval.items())
    )

    cost_line = (
        f"${meta.known_cost:.4f} across {meta.costed_trials} costed trials"
        if meta.costed_trials
        else "no pricing data recorded"
    )
    errors_value = (
        f'<span class="errors">{meta.errors}</span>' if meta.errors else "0"
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>LLM preference-bias report</title>
<link rel="icon" href="data:,">
<style>{CSS}</style>
</head>
<body>
<header>
<h1>LLM preference-bias report</h1>
<p>Forced-choice tendencies: does a stated preference bend the answer, and does option order matter?</p>
</header>
<main>{sections}</main>
<footer>
<dl>
<dt>Models</dt><dd>{html.escape(", ".join(meta.models))}</dd>
<dt>Evals</dt><dd>{html.escape(", ".join(meta.evals))}</dd>
<dt>Trials</dt><dd>{meta.trials} ({errors_value} errored)</dd>
<dt>Collected</dt><dd>{html.escape(meta.first_seen)} &ndash; {html.escape(meta.last_seen)} UTC</dd>
<dt>Cost</dt><dd>{html.escape(cost_line)}</dd>
</dl>
<p>Generated by llm-biases. A broad-brush instrument, not science.</p>
</footer>
</body>
</html>
"""


def write_report(trials: list[Trial], output_path: str) -> str:
    with open(output_path, "w") as f:
        f.write(render_html(trials))
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render a trials JSONL as a self-contained HTML report")
    parser.add_argument("trials_file", help="JSONL written by main.py")
    parser.add_argument("-o", "--output", help="output path (default: input with .html suffix)")
    args = parser.parse_args()

    output = args.output or (
        args.trials_file.removesuffix(".jsonl") + ".html"
    )
    write_report(load_trials(args.trials_file), output)
    print(f"Report written to {output}")


if __name__ == "__main__":
    main()
