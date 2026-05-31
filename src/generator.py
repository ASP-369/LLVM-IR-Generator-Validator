"""
LLVM IR Generator Module

Generates syntactically correct LLVM IR code from natural language
descriptions using Groq's LLaMA 3.3 70B model.
"""

import re
import os
from groq import Groq
from .prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLE

# Initialize Groq client
client = Groq(api_key=os.environ.get("GROQ_API_KEY", ""))


def generate_llvm_ir(
    seed: str,
    temperature: float = 0.4,
    max_tokens: int = 1500,
    model: str = "llama-3.3-70b-versatile",
) -> str:
    """
    Generate LLVM IR code from a natural language seed description.

    Args:
        seed (str): Natural language description of desired IR program
                   (e.g., "fibonacci sequence with loops")
        temperature (float): Generation randomness, 0.0-1.0
                           0.1: deterministic, 1.0: creative
                           Default: 0.4 (balanced)
        max_tokens (int): Maximum output length in tokens
                         Default: 1500
        model (str): Groq model to use
                    Default: "llama-3.3-70b-versatile"

    Returns:
        str: Generated LLVM IR code (no markdown, pure IR text)

    Raises:
        ValueError: If seed is empty
        RuntimeError: If Groq API call fails
        KeyError: If GROQ_API_KEY not set

    Example:
        >>> ir = generate_llvm_ir("add two numbers")
        >>> assert "target triple" in ir
        >>> assert "define i32 @main" in ir
    """
    if not seed or not seed.strip():
        raise ValueError("Seed description cannot be empty")

    # Verify API key
    if not client.api_key:
        raise KeyError("GROQ_API_KEY environment variable not set")

    # Build prompt with seed
    prompt = _build_prompt(seed)

    # Call Groq API
    try:
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as e:
        raise RuntimeError(f"Groq API call failed: {e}")

    # Extract and clean response
    raw_ir = response.choices[0].message.content or ""
    clean_ir = _clean_ir_output(raw_ir)

    return clean_ir


def _build_prompt(seed: str) -> str:
    """
    Construct the prompt for IR generation.

    Args:
        seed (str): Theme/description for IR program

    Returns:
        str: Formatted prompt with few-shot example
    """
    return f"""\
Reference LLVM IR (LLVM 14, x86_64):

{FEW_SHOT_EXAMPLE}

Generate a NEW, complete, valid LLVM IR program with the theme: "{seed}"

Requirements:
1. Include target datalayout and target triple.
2. Use at least one function besides @main.
3. Demonstrate: arithmetic operations, a conditional branch (icmp + br), alloca/load/store, printf.
4. Return 0 from @main.
5. Output ONLY raw LLVM IR — no markdown, no backticks, no comments outside IR syntax.
"""


def _clean_ir_output(raw_text: str) -> str:
    """
    Remove markdown artifacts from generated IR.

    Args:
        raw_text (str): Raw response from model (may contain markdown)

    Returns:
        str: Cleaned LLVM IR text

    Example:
        >>> raw = "```llvm\\ndefine i32...\\n```"
        >>> clean = _clean_ir_output(raw)
        >>> assert "```" not in clean
    """
    # Remove markdown code fences
    text = re.sub(r"```[a-zA-Z]*\n?", "", raw_text)
    text = text.replace("```", "")

    # Remove leading/trailing whitespace
    text = text.strip()

    return text
