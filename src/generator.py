"""
LLVM IR Generator Module

Generates syntactically correct LLVM IR code from natural language
descriptions using NVIDIA's Kimi K2.6 model (or Groq LLaMA as fallback).
"""

import re
import os
import json
import requests
from .prompts import SYSTEM_PROMPT, FEW_SHOT_EXAMPLE

# ---------------------------------------------------------------------------
# API configuration — pick NVIDIA (Kimi K2.6) or Groq based on env vars
# ---------------------------------------------------------------------------
NVIDIA_API_KEY = os.environ.get("NVIDIA_API_KEY", "")
NVIDIA_MODEL = os.environ.get("NVIDIA_MODEL", "moonshotai/kimi-k2.6")
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

# Prefer NVIDIA if key is set, else fall back to Groq
USE_NVIDIA = bool(NVIDIA_API_KEY)

# Lazy-init Groq client only when needed
_groq_client = None


def _get_groq_client():
    global _groq_client
    if _groq_client is None:
        from groq import Groq
        _groq_client = Groq(api_key=GROQ_API_KEY)
    return _groq_client


def _call_nvidia(messages, temperature=0.3, max_tokens=2048):
    """Call NVIDIA NIM API (Kimi K2.6) using requests."""
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    payload = {
        "model": NVIDIA_MODEL,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 1.0,
        "stream": False,
    }
    resp = requests.post(NVIDIA_URL, headers=headers, json=payload, timeout=120)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _call_groq(messages, temperature=0.3, max_tokens=2048, model=None):
    """Call Groq API using the groq SDK."""
    client = _get_groq_client()
    if not client.api_key:
        raise KeyError("GROQ_API_KEY environment variable not set")
    response = client.chat.completions.create(
        model=model or GROQ_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=messages,
    )
    return response.choices[0].message.content or ""


def _call_llm(messages, temperature=0.3, max_tokens=2048):
    """Dispatch to the configured LLM backend."""
    if USE_NVIDIA:
        return _call_nvidia(messages, temperature, max_tokens)
    else:
        return _call_groq(messages, temperature, max_tokens)


def get_backend_info():
    """Return a string describing the active backend for UI display."""
    if USE_NVIDIA:
        return f"NVIDIA NIM ({NVIDIA_MODEL})"
    else:
        return f"Groq ({GROQ_MODEL})"


def generate_llvm_ir(
    seed: str,
    temperature: float = 0.3,
    max_tokens: int = 2048,
    model: str = None,
) -> str:
    """
    Generate LLVM IR code from a natural language seed description.

    Args:
        seed (str): Natural language description of desired IR program
                   (e.g., "fibonacci sequence with loops")
        temperature (float): Generation randomness, 0.0-1.0
                            Default: 0.3 (balanced)
        max_tokens (int): Maximum output length in tokens
                          Default: 2048
        model (str): Override model name (optional)

    Returns:
        str: Generated LLVM IR code (no markdown, pure IR text)

    Raises:
        ValueError: If seed is empty
        RuntimeError: If API call fails

    Example:
        >>> ir = generate_llvm_ir("add two numbers")
        >>> assert "target triple" in ir
        >>> assert "define i32 @main" in ir
    """
    if not seed or not seed.strip():
        raise ValueError("Seed description cannot be empty")

    # Verify at least one API key
    if not NVIDIA_API_KEY and not GROQ_API_KEY:
        raise KeyError("No API key set. Set NVIDIA_API_KEY or GROQ_API_KEY.")

    # Build prompt with seed
    prompt = _build_prompt(seed)

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": prompt},
    ]

    try:
        raw_ir = _call_llm(messages, temperature, max_tokens)
    except Exception as e:
        raise RuntimeError(f"LLM API call failed: {e}")

    # Extract and clean response
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
    Remove markdown artifacts from generated IR, then auto-fix common
    off-by-N errors in C-string constant declarations.

    Args:
        raw_text (str): Raw response from model (may contain markdown)

    Returns:
        str: Cleaned LLVM IR text

    Example:
        >>> raw = "```llvm\\ndefine i32...\\n```"
        >>> clean = _clean_ir_output(raw)
        >>> assert "```" not in clean
    """
    # Strip thinking blocks (Kimi K2 includes <think>...</think>)
    text = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)

    text = re.sub(r"```[a-zA-Z]*\n?", "", text)
    text = text.replace("```", "")

    # Remove any prose lines before the first IR line
    lines = text.split("\n")
    ir_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith("target ") or stripped.startswith("@") or \
           stripped.startswith("define ") or stripped.startswith("declare ") or \
           stripped.startswith(";"):
            ir_start = i
            break
    text = "\n".join(lines[ir_start:])

    text = _fix_cstring_sizes(text)
    text = _name_anonymous_params(text)
    text = _reorder_phi_nodes(text)
    text = _dedupe_declare(text)
    text = _hoist_globals(text)
    text = _add_missing_declares(text)
    text = _rename_duplicate_registers(text)
    text = text.strip()
    return text


def _fix_cstring_sizes(text: str) -> str:
    """
    Fix mismatched [N x i8] sizes for C-string constant declarations.
    Also ensures that strings are null-terminated (\\00) to prevent lli segfaults.
    """
    lines = text.splitlines()
    out = []
    pattern = re.compile(
        r'(@\w+)\s*=\s*(private\s+)?'
        r'(unnamed_addr\s+)?'
        r'(constant|global)\s+'
        r'\[(\d+)\s+x\s+i8\]\s+'
        r'c"([^"]*)"'
    )
    for line in lines:
        m = pattern.search(line)
        if m:
            raw_str = m.group(6)
            
            # Ensure null-termination
            if not raw_str.endswith('\\00'):
                raw_str += '\\00'
                # Update the string in the line
                line = line[:m.start(6)] + raw_str + line[m.end(6):]
                
            # Count actual bytes: each \\XX escape = 1 byte, each normal char = 1 byte
            byte_count = 0
            i_ch = 0
            while i_ch < len(raw_str):
                if raw_str[i_ch] == '\\' and i_ch + 2 < len(raw_str):
                    byte_count += 1
                    i_ch += 3  # skip \XX
                else:
                    byte_count += 1
                    i_ch += 1
                    
            declared_n = int(m.group(5))
            if declared_n != byte_count:
                line = line.replace(f"[{declared_n} x i8]", f"[{byte_count} x i8]")
        out.append(line)
    return "\n".join(out)


def _hoist_globals(text: str) -> str:
    """
    Move global constant definitions (@name = ...) to the top of the file,
    after target datalayout/triple and declare lines but before any define.
    LLMs sometimes place globals after function definitions, which causes
    'Symbols not found' errors at runtime.
    """
    lines = text.splitlines()
    target_lines = []
    declare_lines = []
    global_lines = []
    other_lines = []
    in_func = False
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("define "):
            in_func = True
            other_lines.append(line)
        elif in_func:
            other_lines.append(line)
            if stripped == "}":
                in_func = False
        elif stripped.startswith("target "):
            target_lines.append(line)
        elif stripped.startswith("declare "):
            declare_lines.append(line)
        elif stripped.startswith("@") and "=" in stripped and not in_func:
            global_lines.append(line)
        elif stripped.startswith(";") or not stripped:
            other_lines.append(line)
        else:
            other_lines.append(line)
    
    result = target_lines
    if global_lines:
        result.append("")
        result.extend(global_lines)
    if declare_lines:
        result.append("")
        result.extend(declare_lines)
    if other_lines:
        result.append("")
        result.extend(other_lines)
    
    return "\n".join(result)


def _name_anonymous_params(text: str) -> str:
    """
    Rename %0, %1 in function parameters to %arg0, %arg1 to avoid clashing with LLVM's auto-numbered registers.
    """
    lines = text.splitlines()
    out = []
    for line in lines:
        if line.strip().startswith("define "):
            m = re.search(r"\((.*?)\)", line)
            if m:
                params = m.group(1)
                new_params = re.sub(r"%(\d+)", r"%arg\1", params)
                line = line[:m.start(1)] + new_params + line[m.end(1):]
        out.append(line)
    return "\n".join(out)


def _reorder_phi_nodes(text: str) -> str:
    """
    Ensure all phi nodes are at the beginning of their basic blocks.
    """
    lines = text.splitlines()
    out = []
    in_func = False
    block_lines = []
    
    def process_block(blines):
        if not blines: return []
        label = blines[0]
        phis = []
        others = []
        for l in blines[1:]:
            if " phi " in l and "=" in l:
                phis.append(l)
            else:
                others.append(l)
        return [label] + phis + others

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("define "):
            in_func = True
            out.append(line)
        elif in_func and stripped == "}":
            in_func = False
            out.extend(process_block(block_lines))
            block_lines = []
            out.append(line)
        elif in_func:
            if stripped.endswith(":") and not stripped.startswith(";"):
                out.extend(process_block(block_lines))
                block_lines = [line]
            else:
                block_lines.append(line)
        else:
            out.append(line)
    return "\n".join(out)


def _dedupe_declare(text: str) -> str:
    lines = text.splitlines()
    seen = set()
    out = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("declare "):
            if stripped in seen:
                continue
            seen.add(stripped)
        out.append(line)
    return "\n".join(out)


def _add_missing_declares(text: str) -> str:
    """
    Add standard declares (printf, scanf, etc) if called but not declared.
    """
    if "call " in text and "@printf" in text and "declare i32 @printf" not in text:
        text = "declare i32 @printf(i8*, ...)\n" + text
    if "call " in text and "@scanf" in text and "declare i32 @scanf" not in text:
        text = "declare i32 @scanf(i8*, ...)\n" + text
    return text


def _rename_duplicate_registers(text: str) -> str:
    """
    Ensure all SSA registers defined in a function have unique names.
    If a register is redefined, it renames it and all its subsequent uses.
    """
    lines = text.splitlines()
    out = []
    
    in_func = False
    func_lines = []
    
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("define "):
            in_func = True
            func_lines = [line]
        elif in_func:
            func_lines.append(line)
            if stripped == "}":
                in_func = False
                out.extend(_process_function_registers(func_lines))
                func_lines = []
        else:
            out.append(line)
            
    return "\n".join(out)


def _process_function_registers(func_lines: list) -> list:
    define_line = func_lines[0]
    
    all_defined = set()
    current_name = {}
    block_defs = {"entry": {}}
    
    # Parse params
    param_matches = re.findall(r"%[-a-zA-Z$._0-9]+", define_line)
    for p in param_matches:
        all_defined.add(p)
        current_name[p] = p
        block_defs["entry"][p] = p
        
    processed_lines = [define_line]
    current_block = "entry"
    
    for line in func_lines[1:-1]:  # Exclude define and }
        stripped = line.strip()
        if not stripped:
            processed_lines.append(line)
            continue
            
        # Check if it's a block label
        if stripped.endswith(":") and not stripped.startswith(";"):
            current_block = stripped[:-1].strip()
            block_defs[current_block] = {}
            processed_lines.append(line)
            continue
            
        # Separate LHS (definition) and RHS (uses)
        if "=" in line and not stripped.startswith(";"):
            left, right = line.split("=", 1)
            
            # LHS register definition
            lhs_match = re.search(r"(%[-a-zA-Z$._0-9]+)", left)
            if lhs_match:
                orig_reg = lhs_match.group(1)
                
                # Replace uses on the RHS first
                new_right = _replace_register_uses(right, current_name, block_defs)
                
                # Process definition
                if orig_reg in all_defined:
                    counter = 1
                    while f"{orig_reg}_{counter}" in all_defined:
                        counter += 1
                    unique_reg = f"{orig_reg}_{counter}"
                else:
                    unique_reg = orig_reg
                    
                all_defined.add(unique_reg)
                current_name[orig_reg] = unique_reg
                if current_block not in block_defs:
                    block_defs[current_block] = {}
                block_defs[current_block][orig_reg] = unique_reg
                
                # Reconstruct line with new register name
                new_left = left.replace(orig_reg, unique_reg, 1)
                processed_lines.append(f"{new_left}={new_right}")
            else:
                new_line = _replace_register_uses(line, current_name, block_defs)
                processed_lines.append(new_line)
        else:
            new_line = _replace_register_uses(line, current_name, block_defs)
            processed_lines.append(new_line)
            
    processed_lines.append(func_lines[-1])
    return processed_lines


def _replace_register_uses(text: str, current_name: dict, block_defs: dict) -> str:
    # First, handle phi node mappings: [ %val, %label ]
    phi_pattern = re.compile(r"\[\s*(%[-a-zA-Z$._0-9]+)\s*,\s*%([-a-zA-Z$._0-9]+)\s*\]")
    
    def phi_replace(match):
        val = match.group(1)
        label = match.group(2)
        unique_val = block_defs.get(label, {}).get(val, current_name.get(val, val))
        return f"[ {unique_val}, %{label} ]"
        
    text = phi_pattern.sub(phi_replace, text)
    
    # Replace other uses of registers not in phi format
    reg_pattern = re.compile(r"(%[-a-zA-Z$._0-9]+)")
    
    def reg_replace(match):
        reg = match.group(1)
        start = match.start()
        if start >= 6 and text[start-6:start] == "label ":
            return reg
        return current_name.get(reg, reg)
        
    return reg_pattern.sub(reg_replace, text)
