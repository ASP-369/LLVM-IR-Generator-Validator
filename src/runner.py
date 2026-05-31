"""
LLVM IR Runner Module

Executes compiled LLVM IR code using the LLVM interpreter (lli).
Captures output and execution status.
"""

import subprocess
import tempfile
import os
from typing import Tuple


def run_ir(ir_path: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Execute LLVM IR file using lli (LLVM interpreter).

    Runs the IR with JIT compilation and captures stdout/stderr.

    Args:
        ir_path (str): Path to .ll (LLVM IR text) file
        timeout (int): Execution timeout in seconds (default: 10)
                      Prevents infinite loops from hanging

    Returns:
        Tuple[bool, str]: (success, output)
            success: True if exit code is 0
            output: Combined stdout + stderr from execution

    Raises:
        FileNotFoundError: If ir_path doesn't exist
        subprocess.TimeoutExpired: If execution exceeds timeout

    Example:
        >>> success, output = run_ir("/tmp/fib.ll", timeout=10)
        >>> if success:
        >>>     print(f"Output: {output}")
    """
    if not os.path.exists(ir_path):
        raise FileNotFoundError(f"IR file not found: {ir_path}")

    try:
        result = subprocess.run(
            ["lli", ir_path],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise subprocess.TimeoutExpired(
            f"Execution timeout: program did not complete within {timeout}s", timeout
        )
    except FileNotFoundError:
        raise RuntimeError("lli (LLVM interpreter) not found. Install LLVM tools.")

    # Combine stdout and stderr
    output = (result.stdout + result.stderr).strip()

    # Return success status and output
    success = result.returncode == 0
    return success, output


def run_ir_text(ir_text: str, timeout: int = 10) -> Tuple[bool, str]:
    """
    Execute LLVM IR from text (not file path).

    Convenience wrapper that writes text to temp file and runs.

    Args:
        ir_text (str): LLVM IR code as string
        timeout (int): Execution timeout in seconds

    Returns:
        Tuple[bool, str]: (success, output)

    Example:
        >>> ir = "define i32 @main() { entry: ret i32 42 }"
        >>> success, output = run_ir_text(ir)
    """
    # Write to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".ll", delete=False) as f:
        f.write(ir_text)
        temp_path = f.name

    try:
        result = run_ir(temp_path, timeout=timeout)
    finally:
        # Clean up temp file
        if os.path.exists(temp_path):
            os.unlink(temp_path)

    return result


def compile_ir_to_binary(ir_path: str, output_path: str = None) -> str:
    """
    Compile LLVM IR to native executable.

    Full compilation pipeline:
    1. llvm-ir → llc → assembly
    2. assembly → as → object file
    3. object file → ld → executable

    Args:
        ir_path (str): Path to .ll file
        output_path (str): Path to output binary (default: remove .ll, add .out)

    Returns:
        str: Path to generated executable

    Raises:
        RuntimeError: If compilation fails
    """
    if not os.path.exists(ir_path):
        raise FileNotFoundError(f"IR file not found: {ir_path}")

    if output_path is None:
        output_path = ir_path.replace(".ll", ".out")

    base = ir_path.replace(".ll", "")

    # Step 1: IR → Assembly (llc)
    asm_file = f"{base}.s"
    result = subprocess.run(
        ["llc", ir_path, "-o", asm_file],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"llc failed: {result.stderr}")

    # Step 2: Assembly → Object (as)
    obj_file = f"{base}.o"
    result = subprocess.run(
        ["as", asm_file, "-o", obj_file],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"as failed: {result.stderr}")

    # Step 3: Object → Executable (gcc/ld)
    result = subprocess.run(
        ["gcc", obj_file, "-o", output_path],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"gcc failed: {result.stderr}")

    # Cleanup intermediate files
    for f in [asm_file, obj_file]:
        if os.path.exists(f):
            os.unlink(f)

    return output_path
