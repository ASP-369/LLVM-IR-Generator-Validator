"""
LLVM IR Generator & Validator - Package Init

Main modules:
- generator: IR generation via Groq LLaMA
- validator: Syntax & semantic validation
- runner: IR execution via lli
- batch_runner: Batch processing framework
- prompts: LLM system prompts and examples
"""

__version__ = "2.0"
__author__ = "CD Course Team"

from .generator import generate_llvm_ir
from .validator import validate_ir
from .runner import run_ir
from .batch_runner import run_batch_tests

__all__ = [
    "generate_llvm_ir",
    "validate_ir",
    "run_ir",
    "run_batch_tests",
]
