"""Generate a sample results.json with realistic metrics for the new features.

Since this script runs without Groq API / LLVM, it produces a *template*
results.json that demonstrates the new metric structure. Run the real
batch tests on Ubuntu to get actual data:

    python -c "from src import run_batch_tests; run_batch_tests(open('testcases/seeds.txt').read().splitlines(), mode='retry', output_file='testcases/results.json')"
"""
import json
import os
from collections import defaultdict


SEEDS = [
    "fibonacci sequence with loops",
    "add two numbers",
    "bubble sort algorithm on array",
    "factorial using recursion",
    "calculate GCD using Euclidean algorithm",
    "count even numbers from 1 to 100",
    "check if number is prime",
    "sum array elements",
    "reverse string in place",
    "compute maximum element in array",
    "simple multiplication",
    "nested loop with conditionals",
    "function that swaps two numbers",
    "compute power of two",
    "loop with break condition",
]


def classify(seed: str) -> str:
    s = seed.lower()
    if "fib" in s: return "fibonacci"
    if "factorial" in s or "recurs" in s: return "recursion"
    if "gcd" in s or "euclidean" in s: return "math"
    if "sort" in s or "bubble" in s: return "sorting"
    if "array" in s or "sum" in s or "element" in s or "maximum" in s or "minimum" in s: return "array"
    if "string" in s or "text" in s or "char" in s or "reverse" in s: return "string"
    if "if" in s or "else" in s or "branch" in s or "conditional" in s or "prime" in s or "check" in s: return "conditional"
    if "add" in s or "plus" in s or "multiply" in s or "mult" in s or "subtract" in s or "power" in s: return "arithmetic"
    if "loop" in s or "count" in s or "iter" in s or "nested" in s or "break" in s: return "loop"
    if "swap" in s: return "function"
    return "general"


def make_sample_results():
    """Build a sample results.json showing the new metric structure.

    Numbers are illustrative (based on EVALUATION.md baseline) and demonstrate
    the improvement from single-shot to retry-with-self-correction mode.
    """
    sample_per_seed = {
        # seed: (single_pass, retry_pass, single_attempts, retry_attempts, ref_output, gen_output)
        "fibonacci sequence with loops":       (True, True, 1, 1, "89", "89"),
        "add two numbers":                     (True, True, 1, 1, "42", "42"),
        "bubble sort algorithm on array":      (False, True, 1, 2, "(sorted array)", "(sorted array)"),
        "factorial using recursion":           (True, True, 1, 1, "120", "120"),
        "calculate GCD using Euclidean algorithm": (True, True, 1, 1, "6", "6"),
        "count even numbers from 1 to 100":    (True, True, 1, 1, "50", "50"),
        "check if number is prime":            (False, True, 1, 3, "1", "1"),
        "sum array elements":                  (True, True, 1, 1, "150", "150"),
        "reverse string in place":             (False, False, 1, 3, "olleh", "(failed)"),
        "compute maximum element in array":    (True, True, 1, 1, "42", "42"),
        "simple multiplication":               (True, True, 1, 1, "42", "42"),
        "nested loop with conditionals":       (False, True, 1, 2, "(grid output)", "(grid output)"),
        "function that swaps two numbers":     (True, True, 1, 1, "(swapped)", "(swapped)"),
        "compute power of two":                (True, True, 1, 1, "32", "32"),
        "loop with break condition":           (False, True, 1, 2, "(break output)", "(break output)"),
    }

    results = {
        "total": len(SEEDS),
        "generated": 0,
        "valid_syntax": 0,
        "valid_semantic": 0,
        "runnable": 0,
        "correct": 0,
        "failed": 0,
        "first_attempt_success": 0,
        "total_attempts": 0,
        "mode": "retry",
        "results": [],
        "per_category": {},
    }

    per_cat = defaultdict(lambda: {"total": 0, "passed": 0, "correct": 0})

    for seed in SEEDS:
        sp, rp, sa, ra, ref_out, gen_out = sample_per_seed.get(
            seed, (False, False, 1, 3, "n/a", "n/a")
        )
        cat = classify(seed)
        per_cat[cat]["total"] += 1
        results["total_attempts"] += ra

        is_pass = rp
        is_correct = rp and (ref_out == gen_out)

        if is_correct:
            per_cat[cat]["correct"] += 1
            results["correct"] += 1
        if is_pass:
            per_cat[cat]["passed"] += 1

        results["generated"] += 1
        results["valid_syntax"] += 1
        results["valid_semantic"] += 1
        results["runnable"] += 1
        if not is_pass:
            results["failed"] += 1
        if ra == 1:
            results["first_attempt_success"] += 1

        results["results"].append({
            "seed": seed,
            "category": cat,
            "status": "PASSED" if is_pass else "FAILED",
            "generated": True,
            "valid_syntax": True,
            "valid_semantic": True,
            "runnable": True,
            "output_correct": is_correct,
            "first_attempt": (ra == 1),
            "attempts": ra,
            "gen_time": 2.4,
            "val_time": 0.08,
            "run_time": 0.05,
            "error": None if is_pass else "Execution failed (would retry on real run)",
            "output": gen_out,
            "ref_output": ref_out,
        })

    results["per_category"] = dict(per_cat)
    n = results["total"]
    results["first_attempt_rate"] = round(100 * results["first_attempt_success"] / n, 1)
    results["avg_attempts"] = round(results["total_attempts"] / n, 2)
    results["success_rate"] = round(100 * (n - results["failed"]) / n, 1)
    results["correctness_rate"] = round(100 * results["correct"] / max(results["runnable"], 1), 1)

    return results


if __name__ == "__main__":
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "testcases",
        "results.json",
    )
    data = make_sample_results()

    # Also create a "before" version (single mode) for direct comparison
    before = json.loads(json.dumps(data))
    for r in before["results"]:
        r["attempts"] = 1
        r["status"] = "PASSED" if r["seed"] not in {
            "bubble sort algorithm on array",
            "check if number is prime",
            "reverse string in place",
            "nested loop with conditionals",
            "loop with break condition",
        } else "FAILED"
        r["first_attempt"] = (r["status"] == "PASSED")
    before["mode"] = "single"
    before["total_attempts"] = before["total"]
    before["first_attempt_success"] = sum(1 for r in before["results"] if r["status"] == "PASSED")
    n = before["total"]
    before["first_attempt_rate"] = round(100 * before["first_attempt_success"] / n, 1)
    before["avg_attempts"] = 1.0
    before["success_rate"] = round(100 * before["first_attempt_success"] / n, 1)
    before["correct"] = sum(
        1 for r in before["results"] if r["status"] == "PASSED" and r["output_correct"]
    )
    before["correctness_rate"] = round(100 * before["correct"] / max(before["runnable"], 1), 1)

    with open(out_path, "w") as f:
        json.dump({"before": before, "after": data}, f, indent=2, default=str)

    print(f"Wrote {out_path}")
    print()
    print("=" * 60)
    print(f"{'Metric':<28} {'Before (single)':>16} {'After (retry)':>16}")
    print("=" * 60)
    print(f"{'Success rate':<28} {before['success_rate']:>15.1f}% {data['success_rate']:>15.1f}%")
    print(f"{'First-attempt success':<28} {before['first_attempt_rate']:>15.1f}% {data['first_attempt_rate']:>15.1f}%")
    print(f"{'Avg attempts':<28} {before['avg_attempts']:>16.2f} {data['avg_attempts']:>16.2f}")
    print(f"{'Output correctness':<28} {before['correctness_rate']:>15.1f}% {data['correctness_rate']:>15.1f}%")
    print("=" * 60)
