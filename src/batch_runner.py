"""
LLVM IR Batch Testing Module

Run multiple IR generation/validation/execution tests in sequence.
Collect metrics and generate reports.
"""

import json
import tempfile
import os
from typing import List, Dict, Any
from .generator import generate_llvm_ir
from .validator import validate_ir
from .runner import run_ir


def run_batch_tests(
    seeds: List[str],
    temperature: float = 0.3,
    timeout: int = 10,
    output_file: str = None,
) -> Dict[str, Any]:
    """
    Run batch tests on multiple seeds.

    For each seed:
    1. Generate IR
    2. Validate (syntax + semantic)
    3. Run (if valid)
    4. Collect metrics

    Args:
        seeds (List[str]): List of seed descriptions
        temperature (float): Generation temperature (default: 0.3 for consistency)
        timeout (int): Execution timeout per IR (default: 10 seconds)
        output_file (str): Path to save results JSON (optional)

    Returns:
        Dict[str, Any]: Results summary with keys:
            - total: Number of seeds
            - generated: Number successfully generated
            - valid_syntax: Number with valid syntax
            - valid_semantic: Number semantically valid
            - runnable: Number that executed (exit 0)
            - results: List of detailed test results

    Example:
        >>> seeds = ["fibonacci", "bubble sort", "factorial"]
        >>> results = run_batch_tests(seeds, output_file="results.json")
        >>> print(f"Valid: {results['valid_semantic']}/{results['total']}")
    """
    results = {
        "total": len(seeds),
        "generated": 0,
        "valid_syntax": 0,
        "valid_semantic": 0,
        "runnable": 0,
        "failed": 0,
        "results": [],
    }

    print(f"Running batch tests on {len(seeds)} seeds...")
    print("=" * 80)

    for i, seed in enumerate(seeds, 1):
        test_result = _run_single_test(seed, temperature, timeout)
        results["results"].append(test_result)

        # Update counters
        if test_result["generated"]:
            results["generated"] += 1
        if test_result["valid_syntax"]:
            results["valid_syntax"] += 1
        if test_result["valid_semantic"]:
            results["valid_semantic"] += 1
        if test_result["runnable"]:
            results["runnable"] += 1
        if test_result["status"] == "FAILED":
            results["failed"] += 1

        # Print progress
        status_icon = "✅" if test_result["status"] == "PASSED" else "❌"
        print(
            f"[{i:2d}/{len(seeds)}] {status_icon} {seed[:50]:50s} | "
            f"Gen:{test_result['generated']} | "
            f"Valid:{test_result['valid_semantic']} | "
            f"Run:{test_result['runnable']}"
        )

    print("=" * 80)
    print(f"Summary:")
    print(f"  Total seeds: {results['total']}")
    print(f"  Generated: {results['generated']}/{results['total']} ({100*results['generated']//results['total']}%)")
    print(f"  Valid (syntax): {results['valid_syntax']}/{results['total']}")
    print(f"  Valid (semantic): {results['valid_semantic']}/{results['total']}")
    print(f"  Runnable (exec OK): {results['runnable']}/{results['total']}")
    print(f"  Failed: {results['failed']}/{results['total']}")

    # Save to file if requested
    if output_file:
        with open(output_file, "w") as f:
            json.dump(results, f, indent=2)
        print(f"  Results saved to: {output_file}")

    return results


def _run_single_test(seed: str, temperature: float, timeout: int) -> Dict[str, Any]:
    """
    Run a single test: generate, validate, run.

    Returns:
        Dict with keys: seed, status, generated, valid_syntax, valid_semantic,
                       runnable, gen_time, val_time, run_time, error, output
    """
    result = {
        "seed": seed,
        "status": "PASSED",
        "generated": False,
        "valid_syntax": False,
        "valid_semantic": False,
        "runnable": False,
        "gen_time": 0,
        "val_time": 0,
        "run_time": 0,
        "error": None,
        "output": None,
    }

    # Step 1: Generate
    try:
        import time

        start = time.time()
        ir = generate_llvm_ir(seed, temperature=temperature)
        result["gen_time"] = time.time() - start
        result["generated"] = True

        # Write to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
            f.write(ir)
            ir_path = f.name
    except Exception as e:
        result["status"] = "FAILED"
        result["error"] = f"Generation failed: {str(e)[:100]}"
        return result

    try:
        # Step 2: Validate
        try:
            import time

            start = time.time()
            is_valid_syntax, status_s, detail_s = _validate_syntax_timing(ir_path)
            is_valid_semantic, status_se, detail_se = _validate_semantic_timing(ir_path)
            result["val_time"] = time.time() - start

            result["valid_syntax"] = is_valid_syntax
            result["valid_semantic"] = is_valid_syntax and is_valid_semantic

            if not result["valid_semantic"]:
                result["status"] = "FAILED"
                detail = detail_s if not is_valid_syntax else detail_se
                result["error"] = f"Validation failed: {detail[:100]}"
                return result

        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = f"Validation error: {str(e)[:100]}"
            return result

        # Step 3: Run (if valid)
        try:
            import time

            start = time.time()
            success, output = run_ir(ir_path, timeout=timeout)
            result["run_time"] = time.time() - start
            result["runnable"] = success
            result["output"] = output[:200]  # Truncate for JSON

            if not success:
                result["status"] = "FAILED"
                result["error"] = f"Execution failed: {output[:100]}"
                return result

        except subprocess.TimeoutExpired:
            result["status"] = "FAILED"
            result["error"] = f"Timeout (>{timeout}s)"
            return result
        except Exception as e:
            result["status"] = "FAILED"
            result["error"] = f"Execution error: {str(e)[:100]}"
            return result

    finally:
        # Cleanup
        if os.path.exists(ir_path):
            os.unlink(ir_path)

    return result


def _validate_syntax_timing(ir_path: str) -> tuple:
    """Helper to validate syntax and return result."""
    import subprocess

    try:
        result = subprocess.run(
            ["llvm-as", ir_path, "-o", "/dev/null"],
            capture_output=True,
            text=True,
            timeout=5,
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
    """Helper to validate semantics and return result."""
    import subprocess

    try:
        result = subprocess.run(
            ["opt", "-verify", "-disable-output", ir_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0:
            error = result.stderr or result.stdout or "Unknown error"
            return False, "SEMANTIC_ERROR", error
        return True, "SEMANTIC_OK", ""
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", "Semantic check timed out"
    except Exception as e:
        return False, "ERROR", str(e)


# Import subprocess for module-level functions
import subprocess
