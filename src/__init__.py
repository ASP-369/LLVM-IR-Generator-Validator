"""
LLVM IR Generator & Validator - Package Init

Main modules:
- generator: IR generation via Groq LLaMA
- validator: Syntax & semantic validation
- runner: IR execution via lli
- correctness: Output verification vs reference
- consensus: Multi-attempt voting + self-correction
- batch_runner: Batch processing framework
- prompts: LLM system prompts and examples
"""

__version__ = "2.1"
__author__ = "CD Course Team"


def _safe_import():
    """Lazily import modules with optional dependencies (groq)."""
    globals_dict = {
        "generate_llvm_ir": None,
        "validate_ir": None,
        "validate_ir_text": None,
        "explain_error": None,
        "run_ir": None,
        "run_ir_text": None,
        "check_correctness": None,
        "find_reference_for_seed": None,
        "parse_expected_info": None,
        "generate_with_consensus": None,
        "generate_with_retry": None,
        "run_batch_tests": None,
    }

    try:
        from .generator import generate_llvm_ir
        globals_dict["generate_llvm_ir"] = generate_llvm_ir
    except ImportError:
        pass

    from .validator import validate_ir, validate_ir_text, explain_error
    globals_dict["validate_ir"] = validate_ir
    globals_dict["validate_ir_text"] = validate_ir_text
    globals_dict["explain_error"] = explain_error

    from .runner import run_ir, run_ir_text
    globals_dict["run_ir"] = run_ir
    globals_dict["run_ir_text"] = run_ir_text

    from .correctness import (
        check_correctness,
        find_reference_for_seed,
        parse_expected_info,
    )
    globals_dict["check_correctness"] = check_correctness
    globals_dict["find_reference_for_seed"] = find_reference_for_seed
    globals_dict["parse_expected_info"] = parse_expected_info

    try:
        from .consensus import generate_with_consensus, generate_with_retry
        globals_dict["generate_with_consensus"] = generate_with_consensus
        globals_dict["generate_with_retry"] = generate_with_retry
    except ImportError:
        pass

    try:
        from .batch_runner import run_batch_tests
        globals_dict["run_batch_tests"] = run_batch_tests
    except ImportError:
        pass

    return globals_dict


_imports = _safe_import()
for _name, _obj in _imports.items():
    if _obj is not None:
        globals()[_name] = _obj


__all__ = [
    "generate_llvm_ir",
    "validate_ir",
    "validate_ir_text",
    "explain_error",
    "run_ir",
    "run_ir_text",
    "check_correctness",
    "find_reference_for_seed",
    "parse_expected_info",
    "generate_with_consensus",
    "generate_with_retry",
    "run_batch_tests",
]
