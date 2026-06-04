# LLVM IR Generator & Validator v2.1

A sophisticated LLVM Intermediate Representation (IR) code generator powered by large language models, now **fully upgraded to run on NVIDIA's API** using the powerful `moonshotai/kimi-k2.6` model. It features interactive validation, output correctness checking, self-correction retry loops, robust LLVM syntax cleanup scripts, and a gorgeous modern Gradio web UI.

---

## What's New in v2.1
- **Powered by NVIDIA 🚀**: Integrated support for NVIDIA's NIM API to generate code using `kimi-k2.6`.
- **Premium Glassmorphism UI**: A complete overhaul of the user interface featuring beautiful typography and dark-mode gradients.
- **Auto-Correction Engine**: Uses a multi-attempt retry loop that reads LLVM compiler errors (`opt --verify`) and feeds them back to the model for self-correction.
- **Robust Post-Processing**: Includes custom Python algorithms that automatically clean up LLVM syntax quirks (e.g. hoisting globals, re-ordering phi nodes, renaming duplicate registers, fixing C-string null-terminators).
- **Better Stability**: Hardened against LLM truncation by explicitly enforcing `@main` presence before validation.

---

## What is This?

This project demonstrates:

- **AI-Driven Code Generation**: Generate valid LLVM IR from natural language seeds
- **Automated Validation**: Performs syntax checking via `llvm-as` and semantic verification with `opt --verify`
- **Output Correctness**: Runs both reference and generated IR, diffs the actual outputs
- **Interactive Execution**: Executes generated IR using `lli` (LLVM interpreter) and captures output
- **Batch Testing**: Run multiple seeds in parallel, get per-category accuracy reports

---

## Features

### Generation Strategies
| Mode | Description | Best For |
|------|-------------|----------|
| `single` | One generation attempt | Fast iteration |
| `retry` | Self-correcting loop, LLM fixes its own errors | High accuracy |
| `consensus` | Generate N candidates, pick best | Maximum reliability |

### UI Tabs
1. **Generate** — 3-column workspace: Input options, syntax-highlighted IR, validation & execution metrics.
2. **Batch Test** — Run all 15 predefined seeds, see a comprehensive summary table + per-category accuracy.
3. **Compare** — Side-by-side reference vs. generated IR with line-by-line diff.
4. **Validate File** — Upload an existing `.ll` file, check syntax and semantics.
5. **About** — Requirements and system information.

---

## Requirements

### System Dependencies
- **LLVM 14+**: `llvm-as`, `opt`, `lli` (required for validation/execution)
- **Clang** compiler (optional, for full compilation pipeline)
- **Python 3.8+**

### Python Packages
```
groq>=0.4.0
gradio>=4.0.0
ipywidgets>=8.0.0
requests
```

---

## Installation

### Option 1: Ubuntu / Debian (Local)

```bash
sudo apt-get update
sudo apt-get install -y llvm clang
pip install -r requirements.txt
export GROQ_API_KEY="gsk_your_key_here"
# or
export NVIDIA_API_KEY="nvapi-your_key_here"
```

### Option 2: macOS

```bash
brew install llvm
pip install -r requirements.txt
export GROQ_API_KEY="gsk_your_key_here"
```

---

## Quick Start

### Launch the Web UI

```bash
python3 app.py
```

Opens browser at `http://localhost:7860`.

### Programmatic Usage

```python
from src import (
    generate_llvm_ir,
    validate_ir_text,
    run_ir_text,
    generate_with_retry,
    run_batch_tests,
)

# Self-correcting retry
result = generate_with_retry("factorial recursion", max_attempts=3)
print(f"Succeeded in {result['attempts']} attempts")
print(result['ir'])

# Output correctness check
ok, status, detail = validate_ir_text(result['ir'], require_main=True)
if ok:
    success, output = run_ir_text(result['ir'])
    print("Execution output:", output)
```

---

## Project Structure

```
LLVM-IR-Generator-Validator/
├── README.md                      # This file
├── app.py                         # Premium Gradio web UI (entry point)
├── test_files/                    # Contains sample valid/invalid .ll files
├── requirements.txt               # Python dependencies
│
├── src/
│   ├── generator.py               # IR generation + robust post-processing cleanup
│   ├── validator.py               # Validation with LLVM utilities & error analysis
│   ├── runner.py                  # lli execution engine
│   ├── correctness.py             # Output diff vs reference
│   ├── consensus.py               # Multi-attempt + self-correction retry loops
│   ├── batch_runner.py            # Batch testing metrics module
│   └── prompts.py                 # Few-shot examples
│
└── testcases/
    ├── seeds.txt                  # 15 predefined test seeds
    ├── expected_outputs/          # Golden reference IR files
    └── results.json               # Test run results
```

---

## The Post-Processing Pipeline

Because large language models often struggle with the rigid exactness of LLVM syntax, we apply several automated post-generation fixes before compilation:

1. **`_hoist_globals`**: Forces all global constants to the top of the IR.
2. **`_reorder_phi_nodes`**: Pushes phi instructions to the absolute top of their basic blocks to resolve dominance errors.
3. **`_rename_duplicate_registers`**: Solves the "multiple definition of local value" error by auto-versioning accidentally duplicated SSA variables.
4. **`_fix_cstring_sizes`**: Fixes mismatched array bounds and forcefully injects missing `\00` null terminators into strings to prevent `lli` segmentation faults.

---

**Last Updated**: June 2026 | **LLVM Version**: 14+ | **Status**: Active Development | **Version**: 2.1
