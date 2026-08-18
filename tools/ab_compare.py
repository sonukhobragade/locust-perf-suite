"""A/B compare two Locust stats CSVs.

Locust CSV is downloaded via:
    curl -s http://localhost:8089/stats/requests/csv > branch_a.csv

Usage:
    python tools/ab_compare.py branch_a.csv branch_b.csv \
        --label-a "feature/translations" \
        --label-b "master" \
        --min-reqs 100 > report.md

Emits a Markdown report with per-endpoint delta tables, regression flags,
and a summary. Designed for branch-to-branch perf compare runs (same VU,
same duration, same endpoints).
"""
import argparse
import csv


P95 = "95%"
P99 = "99%"
P50 = "50%"
NAME = "Name"
METHOD = "Type"
REQS = "Request Count"
FAILS = "Failure Count"
AVG = "Average Response Time"


def load(path):
    with open(path) as f:
        rows = list(csv.DictReader(f))
    out = {}
    for r in rows:
        if r[NAME] == "Aggregated":
            continue
        key = f"{r[METHOD]} {r[NAME]}"
        out[key] = {
            "reqs": int(r[REQS]),
            "fails": int(r[FAILS]),
            "p50": float(r[P50]),
            "p95": float(r[P95]),
            "p99": float(r[P99]),
            "avg": float(r[AVG]),
        }
    return out


def fmt_delta(a, b):
    d = b - a
    pct = (d / a * 100) if a else 0
    sign = "+" if d > 0 else ""
    return d, pct, f"{sign}{d:.0f} ({sign}{pct:.0f}%)"


def flag(pct_p95):
    if pct_p95 > 25:
        return "❌ regression"
    if pct_p95 > 10:
        return "⚠️ minor"
    if pct_p95 < -10:
        return "✅ improved"
    return "≈ flat"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("csv_a")
    ap.add_argument("csv_b")
    ap.add_argument("--label-a", default="A")
    ap.add_argument("--label-b", default="B")
    ap.add_argument("--min-reqs", type=int, default=100,
                    help="skip endpoints with fewer reqs in either branch")
    args = ap.parse_args()

    a = load(args.csv_a)
    b = load(args.csv_b)

    matched = sorted(set(a) & set(b))
    skipped = []
    rows = []
    for ep in matched:
        if a[ep]["reqs"] < args.min_reqs or b[ep]["reqs"] < args.min_reqs:
            skipped.append((ep, a[ep]["reqs"], b[ep]["reqs"]))
            continue
        d_p95, pct_p95, _ = fmt_delta(a[ep]["p95"], b[ep]["p95"])
        d_p50, pct_p50, _ = fmt_delta(a[ep]["p50"], b[ep]["p50"])
        rows.append({
            "ep": ep,
            "a_reqs": a[ep]["reqs"], "b_reqs": b[ep]["reqs"],
            "a_p50": a[ep]["p50"], "b_p50": b[ep]["p50"],
            "a_p95": a[ep]["p95"], "b_p95": b[ep]["p95"],
            "d_p95": d_p95, "pct_p95": pct_p95,
            "d_p50": d_p50, "pct_p50": pct_p50,
            "flag": flag(pct_p95),
        })

    only_a = sorted(set(a) - set(b))
    only_b = sorted(set(b) - set(a))

    rows_by_p95 = sorted(rows, key=lambda r: r["pct_p95"], reverse=True)
    regressions = [r for r in rows if r["pct_p95"] > 10]
    improvements = [r for r in rows if r["pct_p95"] < -10]
    flat = [r for r in rows if -10 <= r["pct_p95"] <= 10]

    avg_pct = sum(r["pct_p95"] for r in rows) / len(rows) if rows else 0

    out = []
    out.append(f"# A/B Compare: {args.label_a} vs {args.label_b}\n")
    out.append(f"- A: `{args.csv_a}` ({sum(v['reqs'] for v in a.values())} reqs across {len(a)} endpoints)")
    out.append(f"- B: `{args.csv_b}` ({sum(v['reqs'] for v in b.values())} reqs across {len(b)} endpoints)")
    out.append(f"- Compared: {len(rows)} endpoints (≥{args.min_reqs} reqs each)")
    out.append(f"- Skipped (low traffic): {len(skipped)}")
    out.append(f"- Avg p95 change: **{avg_pct:+.1f}%** ({args.label_b} vs {args.label_a})\n")

    out.append("## Summary")
    out.append(f"- ❌ Regressions (>+10% p95): **{len(regressions)}**")
    out.append("- ⚠️ Minor (>+10% p95, <+25%): see table")
    out.append(f"- ✅ Improvements (<-10% p95): **{len(improvements)}**")
    out.append(f"- ≈ Flat: **{len(flat)}**\n")

    out.append("## All endpoints (sorted by p95 delta % desc)\n")
    out.append("| Endpoint | A reqs | B reqs | A p95 | B p95 | Δp95 | A p50 | B p50 | Δp50 | Flag |")
    out.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---|")
    for r in rows_by_p95:
        out.append(
            f"| `{r['ep']}` | {r['a_reqs']} | {r['b_reqs']} | "
            f"{r['a_p95']:.0f} | {r['b_p95']:.0f} | {r['d_p95']:+.0f} ({r['pct_p95']:+.0f}%) | "
            f"{r['a_p50']:.0f} | {r['b_p50']:.0f} | {r['d_p50']:+.0f} ({r['pct_p50']:+.0f}%) | "
            f"{r['flag']} |"
        )

    if regressions:
        out.append("\n## Top regressions")
        for r in sorted(regressions, key=lambda x: x["pct_p95"], reverse=True)[:10]:
            out.append(f"- `{r['ep']}` p95 {r['a_p95']:.0f} → {r['b_p95']:.0f} ms ({r['pct_p95']:+.0f}%)")

    if improvements:
        out.append("\n## Top improvements")
        for r in sorted(improvements, key=lambda x: x["pct_p95"])[:10]:
            out.append(f"- `{r['ep']}` p95 {r['a_p95']:.0f} → {r['b_p95']:.0f} ms ({r['pct_p95']:+.0f}%)")

    if skipped:
        out.append(f"\n## Skipped endpoints (<{args.min_reqs} reqs in either branch)")
        for ep, ar, br in skipped:
            out.append(f"- `{ep}` (A={ar}, B={br})")

    if only_a:
        out.append(f"\n## Only in {args.label_a}")
        for ep in only_a:
            out.append(f"- `{ep}` ({a[ep]['reqs']} reqs)")
    if only_b:
        out.append(f"\n## Only in {args.label_b}")
        for ep in only_b:
            out.append(f"- `{ep}` ({b[ep]['reqs']} reqs)")

    print("\n".join(out))


if __name__ == "__main__":
    main()
