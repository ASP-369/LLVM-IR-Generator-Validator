"""
LLVM IR Validator Module

Validates LLVM IR using two-stage pipeline:
1. Syntax checking (llvm-as)
2. Semantic verification (opt --verify)
"""

import subprocess
import tempfile
import os
from typing import Tuple


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
            detailed_error: Error details or success message

    Raises:
        FileNotFoundError: If ir_path doesn't exist

    Example:
        >>> is_valid, status, detail = validate_ir("/tmp/test.ll")
        >>> if is_valid:
        >>>     print("IR is valid!")
    """
    if not os.path.exists(ir_path):
        raise FileNotFoundError(f"IR file not found: {ir_path}")

    # Stage 1: Syntax validation via llvm-as
    is_valid, status, detail = _validate_syntax(ir_path)
    if not is_valid:
        return False, "SYNTAX ERROR", detail

    # Stage 2: Semantic validation via opt --verify
    is_valid, status, detail = _validate_semantic(ir_path)
    if not is_valid:
        return False, "SEMANTIC ERROR", detail

    return True, "VALID", "All checks passed (llvm-as + opt --verify)."


def _validate_syntax(ir_path: str) -> Tuple[bool, str, str]:
    """
    Check IR syntax using llvm-as.

    Args:
        ir_path (str): Path to .ll file

    Returns:
        Tuple[bool, str, str]: (success, status, error_message)
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
        return False, "NOT_FOUND", "llvm-as not installed"

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "Unknown syntax error"
        return False, "SYNTAX_ERROR", error_msg.strip()

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

    Args:
        ir_path (str): Path to .ll file

    Returns:
        Tuple[bool, str, str]: (success, status, error_message)
    """
    try:
        result = subprocess.run(
            ["opt", "-verify", "-disable-output", ir_path],
            capture_output=True,
            text=True,
            timeout=5,
        )
    except subprocess.TimeoutExpired:
        return False, "TIMEOUT", "opt timed out (>5 seconds)"
    except FileNotFoundError:
        return False, "NOT_FOUND", "opt not installed"

    if result.returncode != 0:
        error_msg = result.stderr or result.stdout or "Unknown semantic error"
        return False, "SEMANTIC_ERROR", error_msg.strip()

    return True, "SEMANTIC_OK", "Semantic validation passed."


def validate_ir_text(ir_text: str) -> Tuple[bool, str, str]:
    """
    Validate LLVM IR from text (not file path).

    Convenience wrapper that writes text to temp file and validates.

    Args:
        ir_text (str): LLVM IR code as string

    Returns:
        Tuple[bool, str, str]: (is_valid, status, detail)

    Example:
        >>> ir = "define i32 @main() { entry: ret i32 0 }"
        >>> is_valid, status, detail = validate_ir_text(ir)
    """
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
        f.write(ir_text)
        temp_path = f.name

    try:
        result = validate_ir(temp_path)
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return result
