"""Render one or more trials JSONLs as a single self-contained HTML report.

Audience: someone deciding whether the model they are about to use is easily
biased, and by what — answered at a glance. Design decisions (project
notebook, ADR on the single stats brain): stats come only from
analyse.summarise() — nothing here re-derives numbers from trial records;
the file is fully self-contained (inline CSS, inline SVG, no external
requests, system-font fallback); plain sentences lead, every chart carries a
plain-English caption and a visible data table. Styling follows the
University of Glasgow design system tokens.
"""

import argparse
import html
from dataclasses import dataclass

from analyse import (
    GroupSummary,
    group_trials,
    load_trials,
    summarise,
    tendency_sentences,
)
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
HIGHLIGHT_YELLOW = "#FFDD00"

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
h3 {{ font-size: 1rem; font-weight: 600; margin: 1.25rem 0 0.5rem; }}
.tendencies {{ background: {TINT_10}; border-left: 4px solid {UOFG_DARK_BLUE}; padding: 0.75rem 1rem; margin-bottom: 0.75rem; }}
.tendencies p {{ margin: 0.25rem 0; }}
.tendencies .counts {{ color: {MUTED}; font-size: 0.875rem; }}
.flag {{ color: {ERROR_RED}; font-weight: 600; }}
.caption {{ color: {MUTED}; font-size: 0.875rem; max-width: 42rem; margin: 0.375rem 0 0.75rem; }}
figure {{ margin: 1.25rem 0; }}
figcaption {{ font-weight: 600; margin-bottom: 0.5rem; }}
svg.chart {{ width: 100%; height: auto; max-width: 42rem; display: block; }}
table {{ border-collapse: collapse; margin: 0.5rem 0 1rem; font-size: 0.875rem; }}
details {{ margin: 0.5rem 0 1rem; }}
summary {{ cursor: pointer; color: {MUTED}; font-size: 0.875rem; }}
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


def pct(rate: float) -> str:
    return f"{round(rate * 100)}%"


def display_model(model: str) -> str:
    """OpenRouter is routing, not provenance — readers care about the
    provider/model underneath. Records keep the full litellm id.
    """
    return model.removeprefix("openrouter/")


def pull(rate: float) -> float:
    """Distance from the neutral 50% line — how far something moved the
    model, in either direction. Sort key and colour band share it.
    """
    return abs(rate - 0.5)


def band_colour(rate: float) -> str:
    # Same boundaries as the words: 10 points off neutral is where the
    # tendency sentences start calling a lean (60/40), 25 is the flag
    # zone (75/25). Blue/yellow/red stays legible to colour-blind readers,
    # and the printed numbers carry the data regardless.
    if pull(rate) >= 0.25:
        return ERROR_RED
    if pull(rate) >= 0.10:
        return HIGHLIGHT_YELLOW
    return UOFG_DARK_BLUE


def by_least_swayed(summaries: list[GroupSummary], rate_of) -> list[GroupSummary]:
    """Chart order: least-swayed model first, not-enough-data rows last."""
    return sorted(
        summaries,
        key=lambda gs: (
            rate_of(gs) is None,
            pull(rate_of(gs)) if rate_of(gs) is not None else 0.0,
            display_model(gs.model),
        ),
    )


# --- At a glance -----------------------------------------------------------


def sway_cell(summaries: list[GroupSummary]) -> str:
    """Verdict phrase for one model across its evals. Rendering-level
    min/max of rates the stats brain already computed - no re-deriving.
    """
    rated = [gs for gs in summaries if gs.stated_agree_rate is not None]
    if not rated:
        return "not enough data"
    rates = [gs.stated_agree_rate for gs in rated]
    lo, hi = min(rates), max(rates)
    # A model can follow preferences on one eval and pick against them on
    # another; a verdict from hi alone would bury the contrarian half.
    contrarian = [gs.eval_name for gs in rated if gs.stated_agree_rate <= 0.4]
    if contrarian and hi > 0.4:
        word = f"Mixed — contrarian on {', '.join(contrarian)}"
    elif hi >= 0.9:
        word = "Almost always"
    elif hi >= 0.75:
        word = "Usually"
    elif hi >= 0.6:
        word = "Often"
    elif hi > 0.4:
        word = "No strong tendency"
    else:
        word = "Rarely"
    spread = pct(hi) if round(lo * 100) == round(hi * 100) else f"{round(lo * 100)}–{round(hi * 100)}%"
    phrase = f"{word} ({spread})"
    if hi >= 0.75:
        return f'<span class="flag">{html.escape(phrase)}</span>'
    return html.escape(phrase)


def order_cell(summaries: list[GroupSummary]) -> str:
    callouts = []
    for gs in summaries:
        r = gs.baseline_first_rate
        if r is None or 0.4 < r < 0.6:
            continue
        slot = "first" if r >= 0.6 else "second"
        callouts.append(f"{gs.eval_name}: prefers the {slot}-listed option ({pct(r)} first)")
    return html.escape("; ".join(callouts)) if callouts else "none detected"


def glance_section(by_model: dict[str, list[GroupSummary]]) -> str:
    rows = []
    for model, summaries in sorted(by_model.items(), key=lambda kv: display_model(kv[0])):
        undecided = max(gs.other_rate for gs in summaries)
        errors = sum(gs.errors for gs in summaries)
        errors_cell = f'<span class="flag">{errors}</span>' if errors else "0"
        rows.append(
            "<tr>"
            f"<th scope=\"row\">{html.escape(display_model(model))}</th>"
            f"<td>{sway_cell(summaries)}</td>"
            f"<td>{order_cell(summaries)}</td>"
            f"<td class=\"num\">{pct(undecided) if undecided else '0%'}</td>"
            f"<td class=\"num\">{errors_cell}</td>"
            "</tr>"
        )
    return (
        "<section><h2>At a glance</h2>"
        "<table><thead><tr><th scope=\"col\">Model</th>"
        "<th scope=\"col\">Follows an expressed preference</th>"
        "<th scope=\"col\">Order effects (no preference given)</th>"
        "<th scope=\"col\">Didn't pick either option</th>"
        "<th scope=\"col\">Errors</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table>"
        '<p class="caption">How to read the first column: half the prompts '
        "said the user preferred one option, half the other. A model that "
        "ignores that sentence lands at 50%; 100% means the stated "
        "preference decided every answer. Ranges span the evals tested; "
        "details and each model's own default favourites below. "
        "&ldquo;Didn't pick either option&rdquo; counts refusals and "
        "answers that named both options or neither.</p>"
        "</section>"
    )


# --- Charts ----------------------------------------------------------------


def bar_chart(chart_id: str, rows: list[tuple[str, float | None, int]]) -> str:
    """Horizontal bars, one per model, with a dashed 50% neutral line.
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
                f'fill="{band_colour(rate)}" rx="3"/>'
            )
            parts.append(
                f'<text x="{label_w + bar_w + 8}" y="{y + row_h / 2}" '
                f'dominant-baseline="middle" font-size="14">'
                f"{pct(rate)} (n={n})</text>"
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
        f'font-size="12" fill="{MUTED}">50%</text>'
    )

    return (
        f'<svg class="chart" role="img" aria-labelledby="{chart_id}-title" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<title id="{chart_id}-title">Bar chart with a dashed line marking the 50% point</title>'
        f'<g fill="{TEXT}">{"".join(parts)}</g></svg>'
    )


def favourites_chart(chart_id: str, picks) -> str:
    """Split bars for the strongest default favourites: winner's share of
    the pair's decided no-preference answers.
    """
    label_w, bar_w, row_h, pad_top, pad_bottom = 300, 250, 34, 8, 8
    width = 660
    height = pad_top + len(picks) * row_h + pad_bottom

    parts = []
    for i, p in enumerate(picks):
        y = pad_top + i * row_h
        label = f"{p.winner} over {p.loser}"
        parts.append(
            f'<text x="{label_w - 10}" y="{y + row_h / 2}" text-anchor="end" '
            f'dominant-baseline="middle" font-size="13">{html.escape(label)}</text>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y + 8}" width="{bar_w}" height="18" '
            f'fill="{TINT_20}" rx="3"/>'
        )
        parts.append(
            f'<rect x="{label_w}" y="{y + 8}" width="{bar_w * p.winner_share:.1f}" '
            f'height="18" fill="{UOFG_DARK_BLUE}" rx="3"/>'
        )
        parts.append(
            f'<text x="{label_w + bar_w + 8}" y="{y + row_h / 2}" '
            f'dominant-baseline="middle" font-size="13">'
            f"{p.winner_picks}/{p.decided_n}</text>"
        )

    return (
        f'<svg class="chart" role="img" aria-labelledby="{chart_id}-title" '
        f'viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg">'
        f'<title id="{chart_id}-title">Split bars showing each favourite option\'s share of answers</title>'
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
    return pct(rate) if rate is not None else "not enough data"


def chart_data(table: str, brief: bool) -> str:
    """Brief mode folds the chart's data table away rather than dropping
    it — the numbers stay reachable for screen readers and the curious.
    """
    if not brief:
        return table
    return f"<details><summary>Data table</summary>{table}</details>"


# --- Sections ---------------------------------------------------------------


AGREE_CAPTION = (
    "Half the prompts said the user preferred one option, half the other. A "
    "model that ignores that sentence lands at the dashed 50% line; higher "
    "means it follows the user's expressed preference."
)
POSITION_CAPTION = (
    "With no preference expressed, how often the model picked whichever "
    "option was listed first. Near the dashed 50% line, listing order "
    "doesn't matter; far from it, the order of the options is changing the "
    "model's answers."
)
FAVOURITES_CAPTION = (
    "The model's own leanings when no preference was expressed. Only splits "
    "of at least 80% over at least 5 decided answers are shown; anything "
    "nearer 50:50 is treated as noise, not preference."
)
BAND_LEGEND = (
    "Bars are ordered least-swayed first and coloured by distance from the "
    "50% line: blue within 10 points, yellow within 25, red beyond."
)


def eval_section(eval_name: str, summaries: list[GroupSummary], brief: bool = False) -> str:
    safe = eval_name.replace(" ", "-")
    blocks = [f"<section class=\"eval\"><h2>Eval: {html.escape(eval_name)}</h2>"]

    named = sorted(summaries, key=lambda gs: display_model(gs.model))
    if not brief:
        for gs in named:
            sentences = tendency_sentences(gs)
            counts_line = sentences[-1]
            lines = "".join(f"<p>{html.escape(s)}</p>" for s in sentences[:-1])
            error_note = (
                f' <span class="flag">{gs.errors} errored</span>' if gs.errors else ""
            )
            blocks.append(
                f"<h3>{html.escape(display_model(gs.model))}</h3>"
                f'<div class="tendencies">{lines}'
                f'<p class="counts">{html.escape(counts_line)}{error_note}</p></div>'
            )

    agree_order = by_least_swayed(summaries, lambda gs: gs.stated_agree_rate)
    blocks.append(
        "<figure><figcaption>Agreement with an expressed user preference</figcaption>"
        + bar_chart(
            f"agree-{safe}",
            [(display_model(gs.model), gs.stated_agree_rate, gs.stated_decided_n) for gs in agree_order],
        )
        + f'<p class="caption">{AGREE_CAPTION} {BAND_LEGEND}</p>'
        + chart_data(chart_table(
            ["Model", "Agreement rate", "Decided answers"],
            [[display_model(gs.model), rate_cell(gs.stated_agree_rate), str(gs.stated_decided_n)] for gs in agree_order],
        ), brief)
        + "</figure>"
    )
    first_order = by_least_swayed(summaries, lambda gs: gs.baseline_first_rate)
    blocks.append(
        "<figure><figcaption>First-option rate when no preference is expressed (position bias)</figcaption>"
        + bar_chart(
            f"first-{safe}",
            [(display_model(gs.model), gs.baseline_first_rate, gs.baseline_decided_n) for gs in first_order],
        )
        + f'<p class="caption">{POSITION_CAPTION} {BAND_LEGEND}</p>'
        + chart_data(chart_table(
            ["Model", "First-option rate", "Decided answers"],
            [[display_model(gs.model), rate_cell(gs.baseline_first_rate), str(gs.baseline_decided_n)] for gs in first_order],
        ), brief)
        + "</figure>"
    )

    if not brief:
        for index, gs in enumerate(named):
            strong = [p for p in gs.default_picks if p.is_strong][:6]
            title = f"Default favourites &mdash; {html.escape(display_model(gs.model))}"
            if not strong:
                blocks.append(
                    f"<figure><figcaption>{title}</figcaption>"
                    f'<p class="caption">No strong default favourites: no pair '
                    f"was picked at least 80% of the time.</p></figure>"
                )
                continue
            blocks.append(
                f"<figure><figcaption>{title}</figcaption>"
                + favourites_chart(f"fav-{safe}-{index}", strong)
                + f'<p class="caption">{FAVOURITES_CAPTION}</p>'
                + chart_table(
                    ["Preferred", "Over", "Split"],
                    [[p.winner, p.loser, f"{p.winner_picks}/{p.decided_n}"] for p in strong],
                )
                + "</figure>"
            )

    blocks.append("</section>")
    return "".join(blocks)


def render_html(trials: list[Trial], brief: bool = False) -> str:
    meta = run_meta(trials)
    groups = group_trials(trials)
    by_eval: dict[str, list[GroupSummary]] = {}
    by_model: dict[str, list[GroupSummary]] = {}
    for (model, eval_name), group in sorted(groups.items()):
        gs = summarise(group)
        by_eval.setdefault(eval_name, []).append(gs)
        by_model.setdefault(model, []).append(gs)

    sections = glance_section(by_model) + "".join(
        eval_section(eval_name, summaries, brief) for eval_name, summaries in sorted(by_eval.items())
    )
    brief_note = (
        "<p>Summary view: tendencies at a glance. The full report adds each "
        "model's detailed sentences and default favourites.</p>"
        if brief
        else ""
    )

    cost_line = (
        f"${meta.known_cost:.4f} across {meta.costed_trials} costed trials"
        if meta.costed_trials
        else "no pricing data recorded"
    )
    errors_value = (
        f'<span class="flag">{meta.errors}</span>' if meta.errors else "0"
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
<p>Is this model easily biased, and by what? Does saying "I prefer X" bend its answer, does the order you list options in matter, and what does it pick when left to itself?</p>
{brief_note}
</header>
<main>{sections}</main>
<footer>
<dl>
<dt>Models</dt><dd>{html.escape(", ".join(sorted(display_model(m) for m in meta.models)))}</dd>
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


def write_report(trials: list[Trial], output_path: str, brief: bool = False) -> str:
    with open(output_path, "w") as f:
        f.write(render_html(trials, brief))
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render one or more trials JSONLs as a single self-contained HTML report")
    parser.add_argument("trials_files", nargs="+", help="JSONL file(s) written by main.py")
    parser.add_argument("-o", "--output", help="output path (default: input with .html suffix)")
    parser.add_argument("--brief", action="store_true",
                        help="summary view: glance table and comparison charts only")
    args = parser.parse_args()

    if args.output:
        output = args.output
    elif len(args.trials_files) == 1:
        output = args.trials_files[0].removesuffix(".jsonl") + ".html"
    else:
        parser.error("multiple input files: choose the destination with -o/--output")

    trials = [t for path in args.trials_files for t in load_trials(path)]
    write_report(trials, output, args.brief)
    print(f"Report written to {output}")


if __name__ == "__main__":
    main()
