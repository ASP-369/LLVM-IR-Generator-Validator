"""
LLVM IR Validator Module

Validates LLVM IR using two-stage pipeline:
1. Syntax checking (llvm-as)
2. Semantic verification (opt --verify)

Provides human-readable error messages and fix suggestions.
"""

import subprocess
import tempfile
import os
import re
from typing import Tuple, Optional, List, Dict


# ---- Common error pattern -> suggestion mapping ----

ERROR_PATTERNS: List[Dict[str, str]] = [
    {
        "pattern": r"use of undeclared identifier '(%\w+)'",
        "category": "ssa_undefined",
        "suggestion": "A register is used before being defined. Check that every %reg has a defining instruction before its use. SSA violation.",
    },
    {
        "pattern": r"Instruction does not dominate all uses",
        "category": "dominance",
        "suggestion": "An instruction is used in a block it does not dominate. Move the definition to the entry block, use a phi node, or restructure control flow.",
    },
    {
        "pattern": r"basic block doesn't have a terminator",
        "category": "missing_terminator",
        "suggestion": "Every basic block must end with a terminator instruction: ret, br, switch, unreachable, or invoke.",
    },
    {
        "pattern": r"expected (\w+) but got (\w+)",
        "category": "type_mismatch",
        "suggestion": "Type mismatch between expected and actual. Ensure i32 stays i32, i32* stays i32*, etc. Check function signatures match calls.",
    },
    {
        "pattern": r"expected integer constant",
        "category": "non_const_arg",
        "suggestion": "An immediate value was expected but a register/variable was provided. Move the value to an alloca and load it, or compute it at compile time.",
    },
    {
        "pattern": r"invalid operand type for instruction",
        "category": "invalid_operand",
        "suggestion": "An operand type is incompatible with the instruction. Check pointer types match (i32* vs i8*), and signedness flags (nsw, nuw).",
    },
    {
        "pattern": r"Cannot select:.*intrinsic",
        "category": "intrinsic_unavailable",
        "suggestion": "An intrinsic is not declared. Add `declare <type> @name(...)` before use, or replace with a regular function call.",
    },
    {
        "pattern": r"@(\w+)\s*declar(ation|ed)",
        "category": "redeclared",
        "suggestion": "Function or global is declared twice. Remove the duplicate declaration.",
    },
    {
        "pattern": r"expected '}'",
        "category": "syntax_braces",
        "suggestion": "Missing closing brace. Count opening { and closing } in each function definition.",
    },
    {
        "pattern": r"target datalayout|target triple",
        "category": "missing_target",
        "suggestion": "Module-level `target datalayout` and `target triple` lines are required. Add them at the top of the IR.",
    },
    {
        "pattern": r"expected (i\d+|float|double|half)",
        "category": "type_error",
        "suggestion": "Type expectation failed. Verify alloca/load/store use matching types and that GEP indices are i64.",
    },
    {
        "pattern": r"function declaration has wrong number of args|wrong number of parameters",
        "category": "arg_count_mismatch",
        "suggestion": "Function called with wrong number of arguments. The call site must match the function definition signature exactly.",
    },
    {
        "pattern": r"PHI node entries do not match predecessors",
        "category": "phi_mismatch",
        "suggestion": "A phi node must have one entry per predecessor block (and only those). Verify [val, %label] pairs match all incoming branches.",
    },
    {
        "pattern": r"invalid getelementptr indices|getelementptr.*index",
        "category": "gep_error",
        "suggestion": "GEP indices must be i64 for the leading dimension and i32 (or i64) for inner. Format: `getelementptr [N x i8], [N x i8]* @str, i64 0, i64 0`",
    },
]


def _categorize_error(stderr: str) -> Dict[str, str]:
    """
    Match stderr against known error patterns and return category + suggestion.

    Returns:
        dict with keys: category, suggestion, matched_pattern (empty if none)
    """
    for entry in ERROR_PATTERNS:
        m = re.search(entry["pattern"], stderr, re.IGNORECASE)
        if m:
            return {
                "category": entry["category"],
                "suggestion": entry["suggestion"],
                "matched_pattern": entry["pattern"],
            }
    return {"category": "unknown", "suggestion": "See raw error below.", "matched_pattern": ""}


def _truncate_error(stderr: str, max_lines: int = 5) -> str:
    """Keep first few lines of error for readability."""
    lines = [l for l in stderr.splitlines() if l.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)
    return "\n".join(lines[:max_lines]) + f"\n... ({len(lines) - max_lines} more lines)"


def validate_ir(ir_path: str) -> Tuple[bool, str, str]:
    """
    Validate LLVM IR file using llvm-as and opt --verify.

    Two-stage validation pipeline:
    - Stage 1 (llvm-as): Syntax checking, parse to bitcode
    - Stage 2 (opt --verify): Semantic validation (SSA form, dominance, etc.)

    Args:
        ir_path (str): Path to .ll (LLVM IR text) file

    Returns:
        Tuple[bool, str, str]: (is_valid, status_message, detailed_error)
            is_valid: True if both stages pass
            status_message: "VALID" or "SYNTAX ERROR" or "SEMANTIC ERROR"
            detailed_error: Error details with category + suggestion
    """
    if not os.path.exists(ir_path):
        raise FileNotFoundError(f"IR file not found: {ir_path}")

    is_valid, status, detail = _validate_syntax(ir_path)
    if not is_valid:
        return False, "SYNTAX ERROR", detail

    is_valid, status, detail = _validate_semantic(ir_path)
    if not is_valid:
        return False, "SEMANTIC ERROR", detail

    return True, "VALID", "All checks passed (llvm-as + opt --verify)."


def _validate_syntax(ir_path: str) -> Tuple[bool, str, str]:
    """
    Check IR syntax using llvm-as.

    Returns:
        Tuple[bool, str, str]: (success, status, error_message_with_suggestion)
    """
    try:
        result = subprocess.run(
            ["llvm-as", ir_path, "-o", "/dev/null"],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", "llvm-as timed out (>5 seconds)"
    except FileNotFoundError:
        return False, "NOT_FOUND", "llvm-as not installed. Install LLVM tools (apt install llvm / choco install llvm)."

    if result.returncode != 0:
        raw = result.stderr or result.stdout or "Unknown syntax error"
        cat = _categorize_error(raw)
        formatted = (
            f"[Category] {cat['category']}\n"
            f"[Suggestion] {cat['suggestion']}\n"
            f"[LLVM Error]\n{_truncate_error(raw)}"
        )
        return False, "SYNTAX_ERROR", formatted

    return True, "SYNTAX_OK", "Syntax check passed."


def _validate_semantic(ir_path: str) -> Tuple[bool, str, str]:
    """
    Check IR semantics using opt --verify.

    Validates:
    - SSA form correctness
    - Dominance properties
    - Type consistency
    - Function signatures
    - Block terminators

    Returns:
        Tuple[bool, str, str]: (success, status, error_message_with_suggestion)
    """
    try:
        result = subprocess.run(
            ["opt", "-passes=verify", "-disable-output", ir_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode != 0 and "not supported" in result.stderr:
            # Fallback for older LLVM versions
            result = subprocess.run(
                ["opt", "-verify", "-disable-output", ir_path],
                capture_output=True,
                text=True,
                timeout=5,
            )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", "opt timed out (>5 seconds)"
    except FileNotFoundError:
        return False, "NOT_FOUND", "opt not installed. Install LLVM tools."

    if result.returncode != 0:
        raw = result.stderr or result.stdout or "Unknown semantic error"
        cat = _categorize_error(raw)
        formatted = (
            f"[Category] {cat['category']}\n"
            f"[Suggestion] {cat['suggestion']}\n"
            f"[LLVM Error]\n{_truncate_error(raw)}"
        )
        return False, "SEMANTIC_ERROR", formatted

    return True, "SEMANTIC_OK", "Semantic validation passed."


def validate_ir_text(ir_text: str, require_main: bool = False) -> Tuple[bool, str, str]:
    """
    Validate LLVM IR from text (not file path).

    Convenience wrapper that writes text to temp file and validates.

    Args:
        ir_text (str): LLVM IR code as string
        require_main (bool): If True, ensure @main is present

    Returns:
        Tuple[bool, str, str]: (is_valid, status, detail)
    """
    if require_main:
        if "define " not in ir_text or ("@main(" not in ir_text and "@main " not in ir_text):
            return False, "MISSING_MAIN", "[Category] missing_main\n[Suggestion] The program is missing the main entry point. Always include define i32 @main()."

    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
        f.write(ir_text)
        temp_path = f.name

    try:
        result = validate_ir(temp_path)
    finally:
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return result


def get_error_category(stderr: str) -> str:
    """Public helper: return error category string for a given stderr."""
    return _categorize_error(stderr)["category"]


def explain_error(stderr: str) -> str:
    """
    Convert LLVM error output to a human-readable explanation.

    Returns:
        Multi-line string with category, suggestion, and original error.
    """
    cat = _categorize_error(stderr)
    return (
        f"Category: {cat['category']}\n"
        f"Suggestion: {cat['suggestion']}\n"
        f"Original:\n{_truncate_error(stderr)}"
    )
