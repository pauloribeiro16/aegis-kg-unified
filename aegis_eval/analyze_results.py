#!/usr/bin/env python3
"""
analyze_results.py — Analyze accumulated evaluation results.

Usage:
    python analyze_results.py --results-dir aegis_eval/results/

Output:
    - Tabela markdown no stdout
    - Ficheiro .md em results/analysis_report_YYYYMMDD_HHMMSS.md
"""

import json
import glob
import sys
from pathlib import Path
from datetime import datetime
from collections import defaultdict
import argparse

try:
    import pandas as pd
except ImportError:
    print("ERROR: pandas not installed. Run: pip install pandas tabulate")
    sys.exit(1)


def load_results(results_dir: str) -> list[dict]:
    """Load all summary_*.json files."""
    pattern = Path(results_dir) / "summary_*.json"
    files = sorted(glob.glob(str(pattern)))

    if not files:
        print(f"ERROR: No summary_*.json files found in {results_dir}")
        sys.exit(1)

    print(f"✓ Found {len(files)} result files")

    results = []
    for f in files:
        with open(f) as fp:
            data = json.load(fp)
            data["_source_file"] = Path(f).name
            results.append(data)

    return results


def compute_trends(results: list[dict]) -> dict:
    """Compute score trends over time by dimension."""
    if not results:
        return {}

    trends = defaultdict(list)
    for r in sorted(results, key=lambda x: x.get("timestamp", "")):
        ts = r.get("timestamp", "unknown")
        for dim, scores in r.get("by_dimension", {}).items():
            trends[dim].append({
                "timestamp": ts,
                "overall_avg": scores.get("overall_avg", 0),
                "query_avg": scores.get("query_avg", 0),
                "answer_avg": scores.get("answer_avg", 0)
            })

    return dict(trends)


def find_unstable_tasks(results: list[dict], top_n: int = 5) -> list[tuple]:
    """Find categories with highest variance across runs."""
    task_scores = defaultdict(list)

    for r in results:
        for cat, data in r.get("by_category", {}).items():
            avg_scores = data.get("avg_scores", {})
            if avg_scores:
                avg = sum(avg_scores.values()) / len(avg_scores)
                task_scores[cat].append(avg)

    variances = []
    for cat, scores in task_scores.items():
        if len(scores) > 1:
            mean = sum(scores) / len(scores)
            variance = sum((s - mean) ** 2 for s in scores) / len(scores)
            variances.append((cat, variance, scores))

    return sorted(variances, key=lambda x: x[1], reverse=True)[:top_n]


def detect_regressions(results: list[dict], threshold: float = 0.10) -> list[dict]:
    """Detect dimensions with >threshold drop between consecutive runs."""
    regressions = []
    sorted_results = sorted(results, key=lambda x: x.get("timestamp", ""))

    for i in range(1, len(sorted_results)):
        prev = sorted_results[i - 1]
        curr = sorted_results[i]

        for dim in prev.get("by_dimension", {}):
            prev_score = prev["by_dimension"][dim].get("overall_avg", 0)
            curr_score = curr["by_dimension"][dim].get("overall_avg", 0)

            if prev_score > 0 and (prev_score - curr_score) / prev_score > threshold:
                regressions.append({
                    "timestamp": curr.get("timestamp"),
                    "dimension": dim,
                    "previous": prev_score,
                    "current": curr_score,
                    "drop_pct": (prev_score - curr_score) / prev_score * 100
                })

    return regressions


def generate_report(results: list[dict], trends: dict, unstable: list, regressions: list) -> str:
    """Generate markdown report."""
    lines = [
        "# AEGIS Eval Analysis Report",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Period:** {results[0].get('timestamp', 'N/A')} to {results[-1].get('timestamp', 'N/A')}",
        f"**Total Runs:** {len(results)}",
        "",
        "## Dimension Trends (Latest vs First)",
    ]

    for dim, data in trends.items():
        if len(data) >= 2:
            first = data[0]["overall_avg"]
            last = data[-1]["overall_avg"]
            change = ((last - first) / first * 100) if first > 0 else 0
            lines.append(f"- **{dim}:** {first:.2f} → {last:.2f} ({change:+.1f}%)")

    lines.extend(["", "## Top 5 Unstable Categories"])
    if unstable:
        for cat, var, scores in unstable:
            lines.append(f"- {cat}: variance={var:.3f} (scores: {', '.join(f'{s:.2f}' for s in scores)})")
    else:
        lines.append("- No unstable categories detected")

    lines.extend(["", "## Regressions Detected (threshold: 10%)"])
    if regressions:
        for r in regressions:
            lines.append(f"- [{r['timestamp']}] {r['dimension']}: {r['previous']:.2f} → {r['current']:.2f} (-{r['drop_pct']:.1f}%)")
    else:
        lines.append("✅ No regressions detected")

    lines.extend(["", "## Pass Rate Evolution"])
    pass_rates = [(r.get("timestamp", "N/A"), r.get("pass_rate", 0)) for r in sorted(results, key=lambda x: x.get("timestamp", ""))]
    for ts, pr in pass_rates:
        lines.append(f"- {ts}: {pr*100:.1f}%")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze AEGIS eval results")
    parser.add_argument("--results-dir", default="aegis_eval/results", help="Directory with summary_*.json files")
    args = parser.parse_args()

    if not Path(args.results_dir).exists():
        print(f"ERROR: Directory {args.results_dir} does not exist")
        sys.exit(1)

    results = load_results(args.results_dir)

    assert len(results) > 0, "Nenhum resultado carregado!"
    print(f"✓ Loaded {len(results)} results")

    trends = compute_trends(results)
    unstable = find_unstable_tasks(results)
    regressions = detect_regressions(results)

    assert len(trends) > 0, "Nenhuma tendência calculada!"
    print(f"✓ Computed trends for {len(trends)} dimensions")

    report = generate_report(results, trends, unstable, regressions)
    print("\n" + "="*60)
    print(report)
    print("="*60)

    output_file = Path(args.results_dir) / f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    with open(output_file, "w") as f:
        f.write(report)
    print(f"\n📄 Report saved to: {output_file}")


if __name__ == "__main__":
    main()
