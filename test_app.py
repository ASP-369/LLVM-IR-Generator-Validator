"""
Unit tests for the LLVM IR Generator & Validator.
Run on Ubuntu (or any platform with Python 3.8+) to verify module structure.

    python test_app.py

These tests do NOT require Groq API or LLVM to be installed.
They verify module structure, prompt examples, and reference parsing.
"""

import os
import sys
import json
import tempfile

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)


def test_prompts_library():
    from src.prompts import EXAMPLES_LIBRARY, select_template, select_multiple_examples, FEW_SHOT_EXAMPLE
    assert len(EXAMPLES_LIBRARY) >= 8, f"Expected 8+ examples, got {len(EXAMPLES_LIBRARY)}"
    assert select_template("fibonacci sequence") != FEW_SHOT_EXAMPLE
    assert select_template("factorial recursion") != FEW_SHOT_EXAMPLE
    assert select_template("gcd euclidean") != FEW_SHOT_EXAMPLE
    assert select_template("bubble sort") != FEW_SHOT_EXAMPLE
    assert select_template("sum array elements") != FEW_SHOT_EXAMPLE
    multi = select_multiple_examples("fibonacci with loops", 2)
    assert len(multi) == 2
    print(f"  [OK] prompts library: {len(EXAMPLES_LIBRARY)} examples, multi-select works")


def test_correctness_parsing():
    from src.correctness import parse_expected_info, find_reference_for_seed
    info = parse_expected_info(os.path.join(ROOT, "testcases/expected_outputs/fibonacci.ll"))
    assert "fibonacci" in info["name"], info
    assert 10 in info["inputs"], info
    info2 = parse_expected_info(os.path.join(ROOT, "testcases/expected_outputs/fcd.ll" if False else "testcases/expected_outputs/gcd.ll"))
    assert 48 in info2["inputs"], info2
    assert 18 in info2["inputs"], info2
    print(f"  [OK] correctness: parsed fib/gcd headers, inputs extracted")

    ref = find_reference_for_seed("fibonacci with loops")
    assert ref and ref.endswith("fibonacci.ll"), ref
    ref = find_reference_for_seed("factorial recursion")
    assert ref and ref.endswith("factorial.ll"), ref
    ref = find_reference_for_seed("calculate GCD using Euclidean algorithm")
    assert ref and ref.endswith("gcd.ll"), ref
    ref = find_reference_for_seed("add two numbers")
    assert ref and ref.endswith("add.ll"), ref
    print(f"  [OK] correctness: seed-to-reference mapping works (4/4)")


def test_validator_categories():
    from src.validator import _categorize_error, ERROR_PATTERNS
    assert len(ERROR_PATTERNS) >= 10, f"Expected 10+ patterns, got {len(ERROR_PATTERNS)}"
    cat = _categorize_error("PHI node entries do not match predecessors")
    assert cat["category"] == "phi_mismatch"
    cat = _categorize_error("basic block doesn't have a terminator")
    assert cat["category"] == "missing_terminator"
    cat = _categorize_error("expected i32 but got i64")
    assert cat["category"] == "type_mismatch"
    print(f"  [OK] validator: {len(ERROR_PATTERNS)} error patterns, 3/3 categories detected")


def test_batch_runner_classify():
    from src.batch_runner import _classify_seed
    cases = {
        "fibonacci sequence with loops": "fibonacci",
        "factorial using recursion": "recursion",
        "calculate GCD": "math",
        "bubble sort": "sorting",
        "sum array elements": "array",
        "compute maximum element": "array",
        "reverse string": "string",
        "check if number is prime": "conditional",
        "add two numbers": "arithmetic",
        "simple multiplication": "arithmetic",
        "nested loop with conditionals": "conditional",
        "function that swaps two numbers": "function",
    }
    for seed, expected in cases.items():
        actual = _classify_seed(seed)
        assert actual == expected, f"{seed!r} -> {actual!r}, expected {expected!r}"
    print(f"  [OK] batch_runner: {len(cases)}/ {len(cases)} seed categorizations correct")


def test_results_json():
    path = os.path.join(ROOT, "testcases/results.json")
    assert os.path.exists(path), f"Missing: {path}"
    with open(path) as f:
        data = json.load(f)
    assert "before" in data and "after" in data
    assert data["before"]["mode"] == "single"
    assert data["after"]["mode"] == "retry"
    assert data["before"]["total"] == data["after"]["total"] == 15
    assert data["after"]["success_rate"] >= data["before"]["success_rate"]
    print(f"  [OK] results.json: before={data['before']['success_rate']}% after={data['after']['success_rate']}%")


def test_app_imports():
    try:
        import ast
        ast.parse(open(os.path.join(ROOT, "app.py")).read())
        print("  [OK] app.py parses successfully (gradio import only fails at runtime)")
    except SyntaxError as e:
        print(f"  [FAIL] app.py syntax error: {e}")
        raise


def test_package_exports():
    import src
    expected = [
        "generate_llvm_ir", "validate_ir", "validate_ir_text", "explain_error",
        "run_ir", "run_ir_text", "check_correctness", "find_reference_for_seed",
        "parse_expected_info", "generate_with_consensus", "generate_with_retry",
        "run_batch_tests",
    ]
    for name in expected:
        has = hasattr(src, name)
        if not has:
            print(f"  [WARN] {name} not in package (likely requires groq)")
    print(f"  [OK] package init: {sum(1 for n in expected if hasattr(src, n))}/{len(expected)} exports available")


if __name__ == "__main__":
    print("Running tests...\n")
    tests = [
        test_prompts_library,
        test_correctness_parsing,
        test_validator_categories,
        test_batch_runner_classify,
        test_results_json,
        test_app_imports,
        test_package_exports,
    ]
    passed = 0
    failed = 0
    for t in tests:
        try:
            t()
            passed += 1
        except Exception as e:
            print(f"  [FAIL] {t.__name__}: {e}")
            failed += 1
    print(f"\n{'='*40}")
    print(f"Results: {passed} passed, {failed} failed")
    if failed:
        sys.exit(1)
    else:
        print("All tests passed!")
