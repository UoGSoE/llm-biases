"""Behavioural distance between models, from existing trial records.

A curiosity, not forensics: build a per-model fingerprint from the stats
brain's outputs (agreement, position, declined rates per eval, plus the
eight shared character-pair preference shares), z-score each dimension,
and report pairwise Euclidean distances, nearest neighbours, and
average-linkage cluster merges. Run from the repo root.
"""

import glob
import math
from collections import defaultdict

from analyse import group_trials, load_trials, summarise


def short(model: str) -> str:
    return model.split("/")[-1]


trials = []
for path in sorted(glob.glob("examples/*.jsonl")):
    trials.extend(load_trials(path))

feats: dict[str, dict[str, float]] = defaultdict(dict)
for (model, eval_name), group in group_trials(trials).items():
    gs = summarise(group)
    feats[model][f"agree:{eval_name}"] = gs.stated_agree_rate
    feats[model][f"first:{eval_name}"] = gs.baseline_first_rate
    feats[model][f"declined:{eval_name}"] = gs.other_rate
    if eval_name == "characters":
        for p in gs.default_picks:
            a, b = sorted((p.winner, p.loser))
            share = p.winner_picks / p.decided_n
            feats[model][f"pick {a} (v {b})"] = share if p.winner == a else 1 - share

models = sorted(feats, key=short)

# Keep only dimensions every model has a value for.
dims = sorted(set.intersection(*(set(f) for f in feats.values())))
missing = sorted(set.union(*(set(f) for f in feats.values())) - set(dims))
usable, dropped = [], []
for d in dims:
    vals = [feats[m][d] for m in models]
    if any(v is None for v in vals):
        dropped.append((d, "not enough data somewhere"))
        continue
    mean = sum(vals) / len(vals)
    std = math.sqrt(sum((v - mean) ** 2 for v in vals) / len(vals))
    if std < 1e-9:
        dropped.append((d, f"unanimous at {vals[0]:.0%} - no signal"))
        continue
    usable.append((d, mean, std))

print(f"{len(models)} models, {len(usable)} usable dimensions")
for d, why in dropped:
    print(f"  dropped: {d} ({why})")
for d in missing:
    print(f"  absent for some models: {d}")
print()

print("Fingerprints (raw values):")
for m in models:
    print(f"  {short(m)}")
    for d, _, _ in usable:
        print(f"    {d:42} {feats[m][d]:.0%}")
print()

vec = {
    m: [(feats[m][d] - mean) / std for d, mean, std in usable] for m in models
}


def dist(a: str, b: str) -> float:
    return math.sqrt(sum((x - y) ** 2 for x, y in zip(vec[a], vec[b])) / len(usable))


print("Distance matrix (z-scored, lower = more alike):")
names = [short(m) for m in models]
w = max(len(n) for n in names)
print(" " * (w + 2) + "  ".join(f"{n[:9]:>9}" for n in names))
for a in models:
    row = "  ".join(f"{dist(a, b):9.2f}" if a != b else f"{'-':>9}" for b in models)
    print(f"{short(a):>{w}}  {row}")
print()

print("Nearest neighbour:")
for a in models:
    b = min((m for m in models if m != a), key=lambda m: dist(a, m))
    print(f"  {short(a):>12} -> {short(b):<12} ({dist(a, b):.2f})")
print()

claude = [m for m in models if "claude" in m]
intra = [dist(a, b) for i, a in enumerate(claude) for b in claude[i + 1:]]
print(f"Yardstick - intra-Claude-family distances: "
      f"min {min(intra):.2f}, max {max(intra):.2f}")
cross = sorted(
    ((dist(a, b), a, b) for i, a in enumerate(models) for b in models[i + 1:]
     if a.split("/")[0] != b.split("/")[0]),
)
print("Closest cross-vendor pairs:")
for d, a, b in cross[:5]:
    marker = "  <- closer than the closest Claude-to-Claude" if d < min(intra) else ""
    print(f"  {d:.2f}  {short(a)} + {short(b)}{marker}")
print()

# Average-linkage agglomerative merges.
clusters: list[list[str]] = [[m] for m in models]
print("Cluster merges (average linkage):")
while len(clusters) > 1:
    best = None
    for i in range(len(clusters)):
        for j in range(i + 1, len(clusters)):
            d = sum(dist(a, b) for a in clusters[i] for b in clusters[j]) / (
                len(clusters[i]) * len(clusters[j])
            )
            if best is None or d < best[0]:
                best = (d, i, j)
    d, i, j = best
    print(f"  {d:5.2f}  [{', '.join(short(m) for m in clusters[i])}] + "
          f"[{', '.join(short(m) for m in clusters[j])}]")
    clusters[i] = clusters[i] + clusters[j]
    del clusters[j]
