"""
LLVM IR Batch Testing Module

Run multiple IR generation/validation/execution tests in sequence.
Collect metrics and generate reports.

v2.0: New metrics
  - first_attempt_success
  - avg_attempts_to_success
  - output_correct (when reference available)
  - per_category accuracy
  - consensus mode (multi-attempt voting)
  - retry mode (self-correction)
"""

import json
import tempfile
import os
import subprocess
import time
from typing import List, Dict, Any, Optional
from collections import defaultdict

from .validator import validate_ir
from .runner import run_ir
from .correctness import find_reference_for_seed, check_correctness


def _get_generator():
    """Lazy import of generator (requires groq)."""
    from .generator import generate_llvm_ir
    return generate_llvm_ir


def run_batch_tests(
    seeds: List[str],
    temperature: float = 0.3,
    timeout: int = 10,
    output_file: Optional[str] = None,
    mode: str = "single",
    max_attempts: int = 1,
    n_consensus: int = 3,
    check_output: bool = True,
) -> Dict[str, Any]:
    """
    Run batch tests on multiple seeds.

    Args:
        seeds: List of seed descriptions
        temperature: Generation temperature
        timeout: Execution timeout per IR (seconds)
        output_file: Path to save results JSON
        mode: One of 'single', 'retry', 'consensus'
        max_attempts: Max retry attempts (mode='retry')
        n_consensus: Number of consensus candidates (mode='consensus')
        check_output: Whether to verify output against reference

    Returns:
        Dict with keys:
            - total, generated, valid_syntax, valid_semantic, runnable, correct, failed
            - first_attempt_success
            - avg_attempts (when attempts > 0)
            - per_category accuracy
            - results (list of detailed records)
    """
    results = {
        "total": len(seeds),
        "generated": 0,
        "valid_syntax": 0,
        "valid_semantic": 0,
        "runnable": 0,
        "correct": 0,
        "failed": 0,
        "first_attempt_success": 0,
        "total_attempts": 0,
        "mode": mode,
        "per_category": defaultdict(lambda: {"total": 0, "passed": 0, "correct": 0}),
        "results": [],
    }

    print(f"Running batch tests on {len(seeds)} seeds (mode={mode})...")
    print("=" * 80)

    for i, seed in enumerate(seeds, 1):
        if mode == "retry":
            test_result = _run_retry_test(seed, temperature, timeout, max_attempts, check_output)
        elif mode == "consensus":
            test_result = _run_consensus_test(seed, temperature, timeout, n_consensus, check_output)
        else:
            test_result = _run_single_test(seed, temperature, timeout, check_output)

        results["results"].append(test_result)
        category = _classify_seed(seed)
        results["per_category"][category]["total"] += 1

        if test_result["status"] == "PASSED":
            results["per_category"][category]["passed"] += 1
        if test_result.get("output_correct"):
            results["per_category"][category]["correct"] += 1
        if test_result.get("first_attempt"):
            results["first_attempt_success"] += 1
        if test_result.get("attempts", 1) > 0:
            results["total_attempts"] += test_result.get("attempts", 1)

        for key in ("generated", "valid_syntax", "valid_semantic", "runnable", "correct", "failed"):
            if test_result.get(key):
                if key in ("generated", "valid_syntax", "valid_semantic", "runnable", "correct"):
                    results[key] += 1
                elif key == "failed":
                    results[key] += 1

        status_icon = "[PASS]" if test_result["status"] == "PASSED" else "[FAIL]"
        correctness = "OK" if test_result.get("output_correct") else ("--" if test_result.get("output_correct") is None else "X")
        print(
            f"[{i:2d}/{len(seeds)}] {status_icon} {category:10s} {seed[:40]:40s} | "
            f"Val:{test_result.get('valid_semantic', 0)} | "
            f"Run:{test_result.get('runnable', 0)} | "
            f"Out:{correctness} | "
            f"Att:{test_result.get('attempts', 1)}"
        )

    results["per_category"] = dict(results["per_category"])
    if results["total"] > 0:
        results["first_attempt_rate"] = round(
            100 * results["first_attempt_success"] / results["total"], 1
        )
        results["avg_attempts"] = round(
            results["total_attempts"] / results["total"], 2
        )
        results["success_rate"] = round(
            100 * (results["total"] - results["failed"]) / results["total"], 1
        )
        if check_output:
            results["correctness_rate"] = round(
                100 * results["correct"] / max(results["runnable"], 1), 1
            )

    print("=" * 80)
    print(f"Summary:")
    print(f"  Total seeds:        {results['total']}")
    print(f"  Generated:          {results['generated']}/{results['total']} ({_pct(results['generated'], results['total'])}%)")
    print(f"  Valid (syntax):     {results['valid_syntax']}/{results['total']}")
    print(f"  Valid (semantic):   {results['valid_semantic']}/{results['total']}")
    print(f"  Runnable:           {results['runnable']}/{results['total']}")
    print(f"  Output correct:     {results['correct']}/{results['runnable']} (when reference available)")
    print(f"  First-attempt rate: {results.get('first_attempt_rate', 'n/a')}%")
    print(f"  Avg attempts:       {results.get('avg_attempts', 'n/a')}")
    print(f"  Failed:             {results['failed']}/{results['total']}")
    print(f"\nPer-category accuracy:")
    for cat, stats in results["per_category"].items():
        if stats["total"] > 0:
            acc = 100 * stats["passed"] / stats["total"]
            cor = 100 * stats["correct"] / max(stats["total"], 1)
            print(f"  {cat:14s}: {stats['passed']}/{stats['total']} pass ({acc:.0f}%), {stats['correct']}/{stats['total']} correct ({cor:.0f}%)")

    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        print(f"\nResults saved to: {output_file}")

    return results


def _classify_seed(seed: str) -> str:
    """Classify a seed into a category for accuracy reporting."""
    s = seed.lower()
    if any(w in s for w in ("fib",)):
        return "fibonacci"
    if any(w in s for w in ("factorial", "recurs")):
        return "recursion"
    if any(w in s for w in ("gcd", "euclidean")):
        return "math"
    if any(w in s for w in ("sort", "bubble", "merge", "quick")):
        return "sorting"
    if any(w in s for w in ("array", "sum", "element", "maximum", "minimum")):
        return "array"
    if any(w in s for w in ("string", "text", "char", "reverse")):
        return "string"
    if any(w in s for w in ("if", "else", "branch", "conditional", "prime", "check")):
        return "conditional"
    if any(w in s for w in ("add", "plus", "multiply", "mult", "subtract", "power")):
        return "arithmetic"
    if any(w in s for w in ("loop", "count", "iter", "nested", "break")):
        return "loop"
    if any(w in s for w in ("swap",)):
        return "function"
    return "general"


def _pct(n: int, total: int) -> int:
    return round(100 * n / total) if total else 0


def _run_single_test(
    seed: str, temperature: float, timeout: int, check_output: bool
) -> Dict[str, Any]:
    """Standard single-attempt test."""
    result = {
        "seed": seed,
        "status": "PASSED",
        "generated": False,
        "valid_syntax": False,
        "valid_semantic": False,
        "runnable": False,
        "output_correct": None,
        "first_attempt": False,
        "attempts": 1,
        "gen_time": 0,
        "val_time": 0,
        "run_time": 0,
        "error": None,
        "output": None,
        "ref_output": None,
    }

    try:
        start = time.time()
        generate_llvm_ir = _get_generator()
        ir = generate_llvm_ir(seed, temperature=temperature)
        result["gen_time"] = time.time() - start
        result["generated"] = True
        result["first_attempt"] = True
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = f"Generation failed: {str(e)[:120]}"
        return result

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
        f.write(ir)
        ir_path = f.name

    try:
        try:
            start = time.time()
            is_valid, status, detail = validate_ir(ir_path)
            result["val_time"] = time.time() - start
            result["valid_syntax"] = "SYNTAX" not in status
            result["valid_semantic"] = is_valid

            if not is_valid:
                result["status"] = "FAILED"
                result["error"] = detail[:200]
                return result
        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = f"Validation error: {str(e)[:120]}"
            return result

        try:
            start = time.time()
            success, output = run_ir(ir_path, timeout=timeout)
            result["run_time"] = time.time() - start
            result["runnable"] = success
            result["output"] = output[:300] if output else None

            if not success:
                result["status"] = "FAILED"
                result["error"] = f"Execution failed (exit != 0): {output[:120]}"
                return result
        except subprocess.TimeoutExpired:
            result["status"] = "FAILED"
            result["error"] = f"Execution timeout (>{timeout}s)"
            return result
        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = f"Execution error: {str(e)[:120]}"
            return result

        if check_output:
            ref_path = find_reference_for_seed(seed)
            if ref_path:
                ck = check_correctness(ir, ref_path, timeout=timeout)
                result["ref_output"] = ck.get("ref_output", "")
                result["output_correct"] = ck.get("correct", False)
                if not result["output_correct"]:
                    result["status"] = "PARTIAL"
    finally:
        if os.path.exists(ir_path):
            os.unlink(ir_path)

    return result


def _run_retry_test(
    seed: str, temperature: float, timeout: int, max_attempts: int, check_output: bool
) -> Dict[str, Any]:
    """Test with retry/self-correction loop."""
    from .consensus import generate_with_retry

    result = {
        "seed": seed,
        "status": "PASSED",
        "generated": False,
        "valid_syntax": False,
        "valid_semantic": False,
        "runnable": False,
        "output_correct": None,
        "first_attempt": False,
        "attempts": 0,
        "gen_time": 0,
        "val_time": 0,
        "run_time": 0,
        "error": None,
        "output": None,
        "ref_output": None,
        "history": [],
    }

    try:
        rc = generate_with_retry(seed, max_attempts=max_attempts, temperature=temperature)
        result["attempts"] = rc["attempts"]
        result["history"] = [
            {"attempt": h["attempt"], "is_valid": h["is_valid"], "error": h.get("error")}
            for h in rc["history"]
        ]
        if not rc["success"] or not rc["ir"]:
            result["status"] = "FAILED"
            result["error"] = f"Failed after {rc['attempts']} attempts"
            return result
        result["generated"] = True
        result["first_attempt"] = (rc["attempts"] == 1)
        ir = rc["ir"]
        result["gen_time"] = sum(h.get("gen_time", 0) for h in rc["history"])
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = f"Generation error: {str(e)[:120]}"
        return result

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
        f.write(ir)
        ir_path = f.name

    try:
        start = time.time()
        is_valid, status, detail = validate_ir(ir_path)
        result["val_time"] = time.time() - start
        result["valid_syntax"] = "SYNTAX" not in status
        result["valid_semantic"] = is_valid

        if not is_valid:
            result["status"] = "FAILED"
            result["error"] = detail[:200]
            return result

        start = time.time()
        success, output = run_ir(ir_path, timeout=timeout)
        result["run_time"] = time.time() - start
        result["runnable"] = success
        result["output"] = output[:300] if output else None

        if not success:
            result["status"] = "FAILED"
            result["error"] = f"Execution failed: {output[:120]}"
            return result

        if check_output:
            ref_path = find_reference_for_seed(seed)
            if ref_path:
                ck = check_correctness(ir, ref_path, timeout=timeout)
                result["ref_output"] = ck.get("ref_output", "")
                result["output_correct"] = ck.get("correct", False)
                if not result["output_correct"]:
                    result["status"] = "PARTIAL"
    finally:
        if os.path.exists(ir_path):
            os.unlink(ir_path)

    return result


def _run_consensus_test(
    seed: str, temperature: float, timeout: int, n_consensus: int, check_output: bool
) -> Dict[str, Any]:
    """Test with multi-attempt consensus voting."""
    from .consensus import generate_with_consensus

    result = {
        "seed": seed,
        "status": "PASSED",
        "generated": False,
        "valid_syntax": False,
        "valid_semantic": False,
        "runnable": False,
        "output_correct": None,
        "first_attempt": False,
        "attempts": n_consensus,
        "valid_candidates": 0,
        "gen_time": 0,
        "val_time": 0,
        "run_time": 0,
        "error": None,
        "output": None,
        "ref_output": None,
    }

    try:
        cons = generate_with_consensus(seed, n_attempts=n_consensus, temperature=temperature)
        result["attempts"] = cons["total"]
        result["valid_candidates"] = cons["valid_count"]
        result["first_attempt"] = (cons["valid_count"] > 0 and cons["best_index"] == 0)

        if not cons["best"]:
            result["status"] = "FAILED"
            result["error"] = "No valid candidate produced"
            return result

        result["generated"] = True
        ir = cons["best"]
        result["gen_time"] = sum(c.get("gen_time", 0) for c in cons["candidates"])
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = f"Consensus generation error: {str(e)[:120]}"
        return result

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
        f.write(ir)
        ir_path = f.name

    try:
        start = time.time()
        is_valid, status, detail = validate_ir(ir_path)
        result["val_time"] = time.time() - start
        result["valid_syntax"] = "SYNTAX" not in status
        result["valid_semantic"] = is_valid

        if not is_valid:
            result["status"] = "FAILED"
            result["error"] = detail[:200]
            return result

        start = time.time()
        success, output = run_ir(ir_path, timeout=timeout)
        result["run_time"] = time.time() - start
        result["runnable"] = success
        result["output"] = output[:300] if output else None

        if not success:
            result["status"] = "FAILED"
            result["error"] = f"Execution failed: {output[:120]}"
            return result

        if check_output:
            ref_path = find_reference_for_seed(seed)
            if ref_path:
                ck = check_correctness(ir, ref_path, timeout=timeout)
                result["ref_output"] = ck.get("ref_output", "")
                result["output_correct"] = ck.get("correct", False)
                if not result["output_correct"]:
                    result["status"] = "PARTIAL"
    finally:
        if os.path.exists(ir_path):
            os.unlink(ir_path)

    return result


# ---- Backward-compatible helpers (legacy API) ----

def _validate_syntax_timing(ir_path: str) -> tuple:
    try:
        result = subprocess.run(
            ["llvm-as", ir_path, "-o", "/dev/null"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            error = result.stderr or result.stdout or "Unknown error"
            return False, "SYNTAX_ERROR", error
        return True, "SYNTAX_OK", ""
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", "Syntax check timed out"
    except Exception as e:
        return False, "ERROR", str(e)


def _validate_semantic_timing(ir_path: str) -> tuple:
    try:
        result = subprocess.run(
            ["opt", "-verify", "-disable-output", ir_path],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            error = result.stderr or result.stdout or "Unknown error"
            return False, "SEMANTIC_ERROR", error
        return True, "SEMANTIC_OK", ""
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", "Semantic check timed out"
    except Exception as e:
        return False, "ERROR", str(e)
