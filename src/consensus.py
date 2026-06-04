"""
Multi-Attempt Consensus Module

Generates IR multiple times and picks the best candidate.
Supports two strategies:
1. Majority vote: prefer the IR that passes validation
2. Diversity: return all distinct valid candidates for user selection
"""

import time
from typing import List, Dict, Any, Optional, Callable
from collections import Counter
from .validator import validate_ir_text


def _get_generator():
    from .generator import generate_llvm_ir
    return generate_llvm_ir


def generate_with_consensus(
    seed: str,
    n_attempts: int = 3,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    validate: bool = True,
) -> Dict[str, Any]:
    """
    Generate IR N times and return the consensus best result.

    Strategy:
    - Generate N candidates
    - Validate each (if validate=True)
    - Pick the first valid one (lowest generation time wins ties)
    - Return all candidates for inspection

    Args:
        seed: Natural language description
        n_attempts: Number of generation attempts (1-10)
        temperature: LLM temperature
        max_tokens: Max tokens per generation
        validate: Whether to validate candidates

    Returns:
        dict with keys:
            - best (str or None): best IR (first valid)
            - best_index (int): index of best IR
            - candidates (list): all generated IRs with metadata
            - valid_count (int): how many passed validation
            - strategy (str): which strategy was used
    """
    n_attempts = max(1, min(n_attempts, 10))

    candidates: List[Dict[str, Any]] = []
    valid_count = 0

    for i in range(n_attempts):
        candidate = {
            "index": i,
            "ir": None,
            "valid_syntax": False,
            "valid_semantic": False,
            "is_valid": False,
            "gen_time": 0.0,
            "error": None,
        }

        try:
            start = time.time()
            generate_llvm_ir = _get_generator()
            ir = generate_llvm_ir(
                seed,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            candidate["ir"] = ir
            candidate["gen_time"] = time.time() - start

            if validate:
                is_valid, status, detail = validate_ir_text(ir, require_main=True)
                candidate["is_valid"] = is_valid
                if "SYNTAX" in status:
                    candidate["valid_syntax"] = is_valid
                else:
                    candidate["valid_syntax"] = True
                if is_valid:
                    candidate["valid_semantic"] = True
                    valid_count += 1
                else:
                    candidate["error"] = detail[:150]
        except Exception as e:
            candidate["error"] = str(e)[:150]

        candidates.append(candidate)

    best_index = -1
    best_ir: Optional[str] = None

    for c in candidates:
        if c["is_valid"]:
            if best_index == -1 or c["gen_time"] < candidates[best_index]["gen_time"]:
                best_index = c["index"]
                best_ir = c["ir"]

    if best_index == -1 and candidates:
        best_index = 0
        best_ir = candidates[0]["ir"]

    return {
        "best": best_ir,
        "best_index": best_index,
        "candidates": candidates,
        "valid_count": valid_count,
        "total": n_attempts,
        "strategy": "first_valid_lowest_time",
        "all_identical": len({c["ir"] for c in candidates if c["ir"]}) <= 1,
    }


def generate_with_retry(
    seed: str,
    max_attempts: int = 3,
    temperature: float = 0.3,
    max_tokens: int = 1500,
    self_correct: bool = True,
) -> Dict[str, Any]:
    """
    Generate IR with retry on validation failure.

    If self_correct is True, feeds the validation error back to the LLM
    and asks it to fix the issue.

    Args:
        seed: Natural language description
        max_attempts: Maximum retry attempts
        temperature: LLM temperature
        max_tokens: Max tokens per generation
        self_correct: Whether to include error feedback in retry prompt

    Returns:
        dict with keys:
            - ir (str or None): final IR
            - attempts (int): number of attempts made
            - success (bool): whether final IR is valid
            - history (list): per-attempt results
    """
    from .prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLE
    from .generator import _call_llm, _clean_ir_output, NVIDIA_API_KEY, GROQ_API_KEY
    import re

    if not NVIDIA_API_KEY and not GROQ_API_KEY:
        raise KeyError("No API key set. Set NVIDIA_API_KEY or GROQ_API_KEY.")

    history: List[Dict[str, Any]] = []
    final_ir: Optional[str] = None
    success = False

    for attempt in range(1, max_attempts + 1):
        attempt_record = {
            "attempt": attempt,
            "ir": None,
            "is_valid": False,
            "error": None,
            "gen_time": 0.0,
            "strategy": "initial" if attempt == 1 else "self_correct",
        }

        if attempt == 1:
            user_prompt = (
                f"Reference LLVM IR (LLVM 14, x86_64):\n\n"
                f"{FEW_SHOT_EXAMPLE}\n\n"
                f"Generate a NEW, complete, valid LLVM IR program with the theme: \"{seed}\"\n\n"
                f"Requirements:\n"
                f"1. Include target datalayout and target triple.\n"
                f"2. Use at least one function besides @main.\n"
                f"3. Demonstrate: arithmetic, conditional branch, alloca/load/store, printf.\n"
                f"4. Return 0 from @main.\n"
                f"5. Output ONLY raw LLVM IR — no markdown, no backticks."
            )
        else:
            prev = history[-1]
            user_prompt = (
                f"The following LLVM IR was generated for theme \"{seed}\" "
                f"but failed validation:\n\n"
                f"```\n{prev['ir']}\n```\n\n"
                f"Validation error:\n{prev['error']}\n\n"
                f"Please fix the error and regenerate the COMPLETE LLVM IR program. "
                f"Output ONLY raw LLVM IR — no markdown, no backticks, no explanations."
            )

        try:
            start = time.time()
            messages = [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ]
            raw_ir = _call_llm(messages, temperature=temperature, max_tokens=max_tokens)
            ir = _clean_ir_output(raw_ir)
            attempt_record["ir"] = ir
            attempt_record["gen_time"] = time.time() - start

            is_valid, status, detail = validate_ir_text(ir, require_main=True)
            attempt_record["is_valid"] = is_valid
            attempt_record["status"] = status

            if is_valid:
                success = True
                final_ir = ir
                history.append(attempt_record)
                break
            else:
                attempt_record["error"] = detail[:300]

        except Exception as e:
            attempt_record["error"] = str(e)[:300]

        history.append(attempt_record)

    return {
        "ir": final_ir,
        "attempts": len(history),
        "success": success,
        "history": history,
    }
