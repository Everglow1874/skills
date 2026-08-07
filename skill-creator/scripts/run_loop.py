#!/usr/bin/env python3
"""
Run the description optimization loop.

This script evaluates and optimizes skill descriptions for better triggering accuracy.
"""

import json
import os
import sys
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Any, Tuple


def load_json_file(file_path: Path) -> Any:
    """Load and parse a JSON file."""
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_json_file(data: Any, file_path: Path) -> None:
    """Save data to a JSON file."""
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def split_eval_set(eval_set: List[Dict[str, Any]], train_ratio: float = 0.6) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Split eval set into train and test sets."""
    import random
    random.shuffle(eval_set)
    split_idx = int(len(eval_set) * train_ratio)
    return eval_set[:split_idx], eval_set[split_idx:]


def run_evaluation(eval_set: List[Dict[str, Any]], skill_path: Path, model: str) -> Dict[str, Any]:
    """
    Run evaluation on a set of queries against a skill.
    
    Returns:
        Dictionary with trigger rates and details
    """
    results = []
    
    for item in eval_set:
        query = item["query"]
        should_trigger = item["should_trigger"]
        
        # Create a temporary file with the query
        with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
            f.write(query)
            temp_file = f.name
        
        try:
            # Run claude with the skill
            cmd = [
                "claude",
                "-p", query,
                "--skill-path", str(skill_path),
                "--model", model
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Check if skill was triggered (simplified check)
            # In reality, this would need more sophisticated detection
            skill_triggered = "skill" in result.stdout.lower() or "skill" in result.stderr.lower()
            
            results.append({
                "query": query,
                "should_trigger": should_trigger,
                "actually_triggered": skill_triggered,
                "correct": skill_triggered == should_trigger
            })
        
        except subprocess.TimeoutExpired:
            results.append({
                "query": query,
                "should_trigger": should_trigger,
                "actually_triggered": False,
                "correct": not should_trigger,
                "error": "timeout"
            })
        
        except Exception as e:
            results.append({
                "query": query,
                "should_trigger": should_trigger,
                "actually_triggered": False,
                "correct": False,
                "error": str(e)
            })
        
        finally:
            # Clean up temporary file
            os.unlink(temp_file)
    
    # Calculate metrics
    total = len(results)
    correct = sum(1 for r in results if r["correct"])
    
    # Calculate trigger rates
    should_trigger_items = [r for r in results if r["should_trigger"]]
    should_not_trigger_items = [r for r in results if not r["should_trigger"]]
    
    true_positive = sum(1 for r in should_trigger_items if r["actually_triggered"])
    false_negative = sum(1 for r in should_trigger_items if not r["actually_triggered"])
    
    true_negative = sum(1 for r in should_not_trigger_items if not r["actually_triggered"])
    false_positive = sum(1 for r in should_not_trigger_items if r["actually_triggered"])
    
    precision = true_positive / (true_positive + false_positive) if (true_positive + false_positive) > 0 else 0
    recall = true_positive / (true_positive + false_negative) if (true_positive + false_negative) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "accuracy": correct / total if total > 0 else 0,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "true_positive": true_positive,
        "false_positive": false_positive,
        "true_negative": true_negative,
        "false_negative": false_negative,
        "details": results
    }


def propose_improvements(current_description: str, eval_results: Dict[str, Any], eval_set: List[Dict[str, Any]]) -> str:
    """
    Use Claude to propose improvements to the skill description.
    
    This is a simplified version - in practice, you'd call Claude's API
    """
    # This would typically call Claude's API to get improvement suggestions
    # For now, return a placeholder
    return current_description


def run_optimization_loop(
    eval_set_path: Path,
    skill_path: Path,
    model: str,
    max_iterations: int = 5,
    verbose: bool = False
) -> Dict[str, Any]:
    """
    Run the full optimization loop.
    
    Returns:
        Dictionary with best description and optimization history
    """
    # Load eval set
    eval_set = load_json_file(eval_set_path)
    
    # Load current skill description
    skill_md_path = skill_path / "SKILL.md"
    with open(skill_md_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract current description (simplified)
    if "description:" in content:
        start_idx = content.find("description:") + len("description:")
        end_idx = content.find("\n", start_idx)
        current_description = content[start_idx:end_idx].strip()
    else:
        current_description = ""
    
    # Split eval set
    train_set, test_set = split_eval_set(eval_set)
    
    best_description = current_description
    best_test_score = 0
    history = []
    
    for iteration in range(max_iterations):
        if verbose:
            print(f"\n=== Iteration {iteration + 1} ===")
        
        # Evaluate current description on train set
        train_results = run_evaluation(train_set, skill_path, model)
        
        if verbose:
            print(f"Train accuracy: {train_results['accuracy']:.2%}")
        
        # Propose improvements
        new_description = propose_improvements(current_description, train_results, train_set)
        
        if verbose:
            print(f"New description: {new_description[:100]}...")
        
        # Update skill description temporarily
        # (In practice, you'd save this to a temp file)
        
        # Evaluate new description on test set
        # (For simplicity, we're using the same evaluation here)
        test_results = run_evaluation(test_set, skill_path, model)
        
        if verbose:
            print(f"Test accuracy: {test_results['accuracy']:.2%}")
        
        # Record history
        history.append({
            "iteration": iteration + 1,
            "description": new_description,
            "train_accuracy": train_results['accuracy'],
            "test_accuracy": test_results['accuracy'],
            "train_results": train_results,
            "test_results": test_results
        })
        
        # Update best if this is better
        if test_results['accuracy'] > best_test_score:
            best_test_score = test_results['accuracy']
            best_description = new_description
        
        current_description = new_description
    
    return {
        "best_description": best_description,
        "best_test_score": best_test_score,
        "history": history
    }


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Run description optimization loop")
    parser.add_argument("--eval-set", required=True, help="Path to eval_set.json")
    parser.add_argument("--skill-path", required=True, help="Path to skill directory")
    parser.add_argument("--model", required=True, help="Model ID to use")
    parser.add_argument("--max-iterations", type=int, default=5, help="Maximum iterations")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output")
    
    args = parser.parse_args()
    
    eval_set_path = Path(args.eval_set)
    skill_path = Path(args.skill_path)
    
    if not eval_set_path.exists():
        print(f"Error: Eval set not found: {eval_set_path}")
        sys.exit(1)
    
    if not skill_path.exists():
        print(f"Error: Skill directory not found: {skill_path}")
        sys.exit(1)
    
    print("Starting description optimization loop...")
    print(f"Eval set: {eval_set_path}")
    print(f"Skill path: {skill_path}")
    print(f"Model: {args.model}")
    print(f"Max iterations: {args.max_iterations}")
    
    try:
        result = run_optimization_loop(
            eval_set_path,
            skill_path,
            args.model,
            args.max_iterations,
            args.verbose
        )
        
        print("\n=== Optimization Complete ===")
        print(f"Best test score: {result['best_test_score']:.2%}")
        print(f"Best description: {result['best_description'][:200]}...")
        
        # Save results
        output_path = skill_path / "optimization_results.json"
        save_json_file(result, output_path)
        print(f"\nResults saved to: {output_path}")
    
    except Exception as e:
        print(f"Error during optimization: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
