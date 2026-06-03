"""
LLVM IR Output Correctness Module

Compares generated IR output against expected reference output.
Parses expected inputs from reference .ll file headers, runs both
IRs with `lli`, and checks if outputs match.
"""

import re
import subprocess
import tempfile
import os
from typing import Tuple, Optional, List


def parse_expected_info(reference_path: str) -> dict:
    """
    Extract expected algorithm info from reference .ll file header.

    Looks for patterns in the header comment:
        ; Fibonacci Sequence (N=10) - Expected Output Reference
        ; GCD Algorithm (48, 18) - Expected Output Reference
        ; Factorial Using Recursion - Expected Output Reference

    Returns:
        dict with keys: name, inputs, raw_header
    """
    if not os.path.exists(reference_path):
        return {"name": "unknown", "inputs": [], "raw_header": ""}

    with open(reference_path, "r") as f:
        first_line = f.readline().strip()

    info = {"name": "unknown", "inputs": [], "raw_header": first_line}

    paren_match = re.search(r"\(([^)]+)\)", first_line)
    if paren_match:
        inputs_str = paren_match.group(1)
        inputs = []
        for token in inputs_str.split(","):
            token = token.strip()
            if "=" in token:
                token = token.split("=")[1].strip()
            try:
                inputs.append(int(token))
            except ValueError:
                pass
        info["inputs"] = inputs

    name_match = re.match(r";\s*([^-]+?)(?:\s*\(|-)", first_line)
    if name_match:
        info["name"] = name_match.group(1).strip().lower()

    return info


def get_reference_output(reference_path: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Run the reference IR and capture its output.

    Args:
        reference_path: Path to reference .ll file
        timeout: Execution timeout in seconds

    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(
            ["lli", reference_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        output = (result.stdout + result.stderr).strip()
        return result.returncode == 0, output
    except (subprocess.TimeoutExpired, FileNotFoundError) as e:
        return False, str(e)


def get_generated_output(ir_text: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Run the generated IR and capture its output.

    Args:
        ir_text: Generated LLVM IR as string
        timeout: Execution timeout in seconds

    Returns:
        Tuple of (success, output)
    """
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
        f.write(ir_text)
        ir_path = f.name

    try:
        try:
            result = subprocess.run(
                ["lli", ir_path],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            output = (result.stdout + result.stderr).strip()
            return result.returncode == 0, output
        except subprocess.TimeoutExpired:
            return False, "TIMEOUT"
        except FileNotFoundError:
            return False, "lli not installed"
    finally:
        if os.path.exists(ir_path):
            os.unlink(ir_path)


def normalize_output(output: str) -> List[str]:
    """
    Normalize program output for comparison.

    Splits on whitespace/newlines, strips empty lines, sorts numerically when possible.
    """
    if not output:
        return []

    lines = []
    for line in output.splitlines():
        line = line.strip()
        if line:
            lines.append(line)
    return lines


def compare_outputs(ref_output: str, gen_output: str) -> dict:
    """
    Compare two program outputs and return detailed diff.

    Returns:
        dict with keys: match, ref_lines, gen_lines, common, missing, extra
    """
    ref_lines = normalize_output(ref_output)
    gen_lines = normalize_output(gen_output)

    ref_set = set(ref_lines)
    gen_set = set(gen_lines)

    common = ref_set & gen_set
    missing = ref_set - gen_set
    extra = gen_set - ref_set

    match = (ref_set == gen_set) and len(ref_lines) == len(gen_lines)

    return {
        "match": match,
        "ref_lines": ref_lines,
        "gen_lines": gen_lines,
        "common": sorted(common),
        "missing": sorted(missing),
        "extra": sorted(extra),
    }


def check_correctness(
    generated_ir: str,
    reference_path: str,
    timeout: int = 10,
) -> dict:
    """
    Full correctness check: run both IRs, compare outputs.

    Args:
        generated_ir: Generated LLVM IR text
        reference_path: Path to reference .ll file
        timeout: Execution timeout per IR

    Returns:
        dict with keys:
            - correct (bool): outputs match exactly
            - reference_info (dict): parsed header info
            - ref_output (str): reference program output
            - gen_output (str): generated program output
            - diff (dict): output of compare_outputs
            - error (str or None): error message if check failed
    """
    result = {
        "correct": False,
        "reference_info": {},
        "ref_output": "",
        "gen_output": "",
        "diff": {},
        "error": None,
    }

    if not os.path.exists(reference_path):
        result["error"] = f"Reference file not found: {reference_path}"
        return result

    info = parse_expected_info(reference_path)
    result["reference_info"] = info

    ref_ok, ref_out = get_reference_output(reference_path, timeout=timeout)
    if not ref_ok:
        result["error"] = f"Reference execution failed: {ref_out[:200]}"
        result["ref_output"] = ref_out
        return result

    gen_ok, gen_out = get_generated_output(generated_ir, timeout=timeout)
    if not gen_ok:
        result["error"] = f"Generated execution failed: {gen_out[:200]}"
        result["gen_output"] = gen_out
        result["ref_output"] = ref_out
        return result

    result["ref_output"] = ref_out
    result["gen_output"] = gen_out
    result["diff"] = compare_outputs(ref_out, gen_out)
    result["correct"] = result["diff"]["match"]

    return result


def find_reference_for_seed(seed: str, references_dir: str = None) -> Optional[str]:
    """
    Find the reference .ll file that best matches a seed.

    Args:
        seed: Natural language seed description
        references_dir: Path to expected_outputs directory

    Returns:
        Path to matching reference .ll, or None
    """
    if references_dir is None:
        references_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "testcases",
            "expected_outputs",
        )

    if not os.path.isdir(references_dir):
        return None

    seed_lower = seed.lower()
    keyword_map = {
        "fibonacci": "fibonacci.ll",
        "fib": "fibonacci.ll",
        "factorial": "factorial.ll",
        "recurs": "factorial.ll",
        "gcd": "gcd.ll",
        "euclidean": "gcd.ll",
        "add": "add.ll",
        "addition": "add.ll",
        "sum": "add.ll",
    }

    for keyword, ref_file in keyword_map.items():
        if keyword in seed_lower:
            ref_path = os.path.join(references_dir, ref_file)
            if os.path.exists(ref_path):
                return ref_path

    return None
