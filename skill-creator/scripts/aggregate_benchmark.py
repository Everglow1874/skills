#!/usr/bin/env python3
"""
Aggregate benchmark results from multiple evaluation runs.

This script processes evaluation results and produces aggregate statistics
including pass rates, timing, and token usage.
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any


def load_json_file(file_path: Path) -> Dict[str, Any]:
    """Load and parse a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: Dict[str, Any], file_path: Path) -> None:
    """Save data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def calculate_statistics(values: List[float]) -> Dict[str, float]:
    """Calculate mean and standard deviation for a list of values."""
    if not values:
        return {"mean": 0.0, "stddev": 0.0}
    
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    stddev = variance ** 0.5
    
    return {"mean": mean, "stddev": stddev}


def process_evaluation(eval_dir: Path) -> Dict[str, Any]:
    """Process a single evaluation directory."""
    result = {
        "eval_name": eval_dir.name,
        "with_skill": None,
        "baseline": None
    }
    
    # Process with_skill run
    with_skill_dir = eval_dir / "with_skill"
    if with_skill_dir.exists():
        timing_file = with_skill_dir / "timing.json"
        grading_file = with_skill_dir / "grading.json"
        
        timing = load_json_file(timing_file) if timing_file.exists() else {}
        grading = load_json_file(grading_file) if grading_file.exists() else {}
        
        # Calculate pass rate from grading
        pass_rate = 0.0
        if "expectations" in grading:
            passed = sum(1 for exp in grading["expectations"] if exp.get("passed", False))
            total = len(grading["expectations"])
            pass_rate = passed / total if total > 0 else 0.0
        
        result["with_skill"] = {
            "pass_rate": pass_rate,
            "time": timing.get("duration_ms", 0),
            "tokens": timing.get("total_tokens", 0)
        }
    
    # Process baseline run
    baseline_dir = eval_dir / "baseline"
    if baseline_dir.exists():
        timing_file = baseline_dir / "timing.json"
        grading_file = baseline_dir / "grading.json"
        
        timing = load_json_file(timing_file) if timing_file.exists() else {}
        grading = load_json_file(grading_file) if grading_file.exists() else {}
        
        # Calculate pass rate from grading
        pass_rate = 0.0
        if "expectations" in grading:
            passed = sum(1 for exp in grading["expectations"] if exp.get("passed", False))
            total = len(grading["expectations"])
            pass_rate = passed / total if total > 0 else 0.0
        
        result["baseline"] = {
            "pass_rate": pass_rate,
            "time": timing.get("duration_ms", 0),
            "tokens": timing.get("total_tokens", 0)
        }
    
    return result


def aggregate_benchmark(workspace_dir: Path, skill_name: str) -> Dict[str, Any]:
    """Aggregate benchmark results from all evaluations in a workspace."""
    evaluations = []
    
    # Find all evaluation directories
    for item in workspace_dir.iterdir():
        if item.is_dir() and item.name.startswith("eval-"):
            eval_result = process_evaluation(item)
            evaluations.append(eval_result)
    
    # Calculate aggregate statistics
    with_skill_pass_rates = [e["with_skill"]["pass_rate"] for e in evaluations if e["with_skill"]]
    with_skill_times = [e["with_skill"]["time"] for e in evaluations if e["with_skill"]]
    with_skill_tokens = [e["with_skill"]["tokens"] for e in evaluations if e["with_skill"]]
    
    baseline_pass_rates = [e["baseline"]["pass_rate"] for e in evaluations if e["baseline"]]
    baseline_times = [e["baseline"]["time"] for e in evaluations if e["baseline"]]
    baseline_tokens = [e["baseline"]["tokens"] for e in evaluations if e["baseline"]]
    
    # Calculate statistics
    with_skill_stats = {
        "pass_rate": calculate_statistics(with_skill_pass_rates),
        "time": calculate_statistics(with_skill_times),
        "tokens": calculate_statistics(with_skill_tokens)
    }
    
    baseline_stats = {
        "pass_rate": calculate_statistics(baseline_pass_rates),
        "time": calculate_statistics(baseline_times),
        "tokens": calculate_statistics(baseline_tokens)
    }
    
    # Calculate delta
    delta = {
        "pass_rate": with_skill_stats["pass_rate"]["mean"] - baseline_stats["pass_rate"]["mean"],
        "time": with_skill_stats["time"]["mean"] - baseline_stats["time"]["mean"],
        "tokens": with_skill_stats["tokens"]["mean"] - baseline_stats["tokens"]["mean"]
    }
    
    return {
        "skill_name": skill_name,
        "configurations": [
            {
                "name": "with_skill",
                "pass_rate": with_skill_stats["pass_rate"]["mean"],
                "mean_time": with_skill_stats["time"]["mean"],
                "stddev_time": with_skill_stats["time"]["stddev"],
                "mean_tokens": with_skill_stats["tokens"]["mean"],
                "stddev_tokens": with_skill_stats["tokens"]["stddev"],
                "evals": [e for e in evaluations if e["with_skill"]]
            },
            {
                "name": "baseline",
                "pass_rate": baseline_stats["pass_rate"]["mean"],
                "mean_time": baseline_stats["time"]["mean"],
                "stddev_time": baseline_stats["time"]["stddev"],
                "mean_tokens": baseline_stats["tokens"]["mean"],
                "stddev_tokens": baseline_stats["tokens"]["stddev"],
                "evals": [e for e in evaluations if e["baseline"]]
            }
        ],
        "delta": delta,
        "evaluations": evaluations
    }


def generate_markdown_report(benchmark: Dict[str, Any]) -> str:
    """Generate a markdown report from benchmark data."""
    lines = [
        f"# Benchmark Report: {benchmark['skill_name']}",
        "",
        "## Summary",
        "",
        f"- **Total Evaluations**: {len(benchmark['evaluations'])}",
        f"- **With Skill Pass Rate**: {benchmark['configurations'][0]['pass_rate']:.2%}",
        f"- **Baseline Pass Rate**: {benchmark['configurations'][1]['pass_rate']:.2%}",
        f"- **Improvement**: {benchmark['delta']['pass_rate']:.2%}",
        "",
        "## Performance",
        "",
        "### With Skill",
        f"- Mean Time: {benchmark['configurations'][0]['mean_time']:.2f}ms",
        f"- Std Dev Time: {benchmark['configurations'][0]['stddev_time']:.2f}ms",
        f"- Mean Tokens: {benchmark['configurations'][0]['mean_tokens']:.2f}",
        f"- Std Dev Tokens: {benchmark['configurations'][0]['stddev_tokens']:.2f}",
        "",
        "### Baseline",
        f"- Mean Time: {benchmark['configurations'][1]['mean_time']:.2f}ms",
        f"- Std Dev Time: {benchmark['configurations'][1]['stddev_time']:.2f}ms",
        f"- Mean Tokens: {benchmark['configurations'][1]['mean_tokens']:.2f}",
        f"- Std Dev Tokens: {benchmark['configurations'][1]['stddev_tokens']:.2f}",
        "",
        "## Evaluations",
        ""
    ]
    
    for i, eval_result in enumerate(benchmark['evaluations'], 1):
        lines.append(f"### {eval_result['eval_name']}")
        if eval_result['with_skill']:
            lines.append(f"- With Skill Pass Rate: {eval_result['with_skill']['pass_rate']:.2%}")
        if eval_result['baseline']:
            lines.append(f"- Baseline Pass Rate: {eval_result['baseline']['pass_rate']:.2%}")
        lines.append("")
    
    return "\n".join(lines)


def main():
    if len(sys.argv) < 3:
        print("Usage: python -m scripts.aggregate_benchmark <workspace_dir> --skill-name <name>")
        sys.exit(1)
    
    workspace_dir = Path(sys.argv[1])
    skill_name = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == "--skill-name" else "unknown"
    
    if not workspace_dir.exists():
        print(f"Error: Workspace directory {workspace_dir} does not exist")
        sys.exit(1)
    
    # Aggregate benchmark
    benchmark = aggregate_benchmark(workspace_dir, skill_name)
    
    # Save benchmark.json
    benchmark_file = workspace_dir / "benchmark.json"
    save_json_file(benchmark, benchmark_file)
    print(f"Saved benchmark data to {benchmark_file}")
    
    # Generate and save markdown report
    markdown_report = generate_markdown_report(benchmark)
    report_file = workspace_dir / "benchmark.md"
    with open(report_file, 'w', encoding='utf-8') as f:
        f.write(markdown_report)
    print(f"Saved markdown report to {report_file}")


if __name__ == "__main__":
    main()
