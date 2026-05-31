# 🔧 LLVM IR Generator & Validator

A sophisticated LLVM Intermediate Representation (IR) code generator powered by Groq's LLaMA 3.3 70B model, featuring interactive validation and execution capabilities.

## What is This?

This project demonstrates:

- **AI-Driven Code Generation**: Uses Groq LLaMA to generate valid LLVM IR from natural language seeds
- **Automated Validation**: Performs syntax checking via `llvm-as` and semantic verification with `opt --verify`
- **Interactive Execution**: Executes generated IR using `lli` (LLVM interpreter) and captures output
- **Batch Testing**: Run multiple seeds in parallel and generate performance reports

## Features

✨ **Core Features**

- Generate syntactically correct LLVM IR from natural language descriptions
- Real-time validation pipeline (syntax → semantic checks)
- Interactive web UI (Jupyter Notebook based)
- Batch testing with pass/fail metrics
- Support for LLVM 14 typed pointers (no opaque pointers)

🎯 **Constraints**

- Generates functions with arithmetic operations, conditionals, memory operations, and I/O
- Ensures `target datalayout` and `target triple` inclusion
- Validates SSA form and proper terminator placement
- Temperature control for generation consistency

## Requirements

### System Dependencies

- LLVM tools (≥14): `llvm-as`, `opt`, `lli`
- Clang compiler
- Python 3.8+

### Python Packages

```
groq>=0.4.0
ipywidgets>=8.0.0
```

## Installation & Setup

### Option 1: Google Colab (Recommended)

```bash
# All dependencies auto-install in Colab environment
# Just run the notebook cells in order
```

### Option 2: Local Linux/WSL

```bash
# Install LLVM
sudo apt-get update
sudo apt-get install -y llvm clang

# Install Python dependencies
pip install groq ipywidgets

# Set Groq API Key
export GROQ_API_KEY="your-key-here"
```

### Option 3: Using Build Scripts

```bash
./build.sh  # Installs dependencies
./run.sh    # Starts Jupyter server
```

## Quick Start

### Interactive Mode

```bash
jupyter notebook LLVm_IR_Generator_v2.ipynb
```

1. **Cell 1**: Install dependencies (run once)
2. **Cell 2**: Set your Groq API Key
3. **Cell 3**: Core logic loads automatically
4. **Cell 4**: Launch interactive UI
   - Enter seed description (e.g., "fibonacci with loop")
   - Click "⚡ Generate IR"
   - Review generated code
   - Click "🔍 Validate IR" to check correctness
   - Click "▶ Run with lli" to execute (if valid)

### Batch Testing Mode

```bash
# Run Cell 5 in notebook, or:
python -c "from src.batch_runner import run_batch_tests; run_batch_tests()"
```

## Project Structure

```
LLVM/
├── README.md                      # This file
├── DESIGN.md                      # Architecture & design decisions
├── IMPLEMENTATION.md              # LLVM IR details & implementation notes
├── EVALUATION.md                  # Test results & performance metrics
├── LLVm_IR_Generator_v2.ipynb     # Main interactive notebook
├── build.sh                       # Dependency installation script
├── run.sh                         # Server startup script
└── src/
    ├── __init__.py
    ├── generator.py               # Core IR generation logic
    ├── validator.py               # Validation pipeline
    ├── runner.py                  # Execution engine
    ├── batch_runner.py            # Batch testing framework
    └── prompts.py                 # LLM system prompts & examples
└── testcases/
    ├── README.md                  # Test documentation
    ├── seeds.txt                  # Predefined test seeds
    ├── expected_outputs/          # Reference outputs
    │   ├── fibonacci.ll
    │   ├── bubble_sort.ll
    │   ├── factorial.ll
    │   └── ...
    └── results.json               # Test run results
```

## Usage Examples

### Example 1: Fibonacci Sequence

```python
from src.generator import generate_llvm_ir
from src.validator import validate_ir
from src.runner import run_ir

seed = "fibonacci sequence with loops"
ir = generate_llvm_ir(seed, temperature=0.4)
is_valid, status, detail = validate_ir(ir)
if is_valid:
    success, output = run_ir(ir)
    print(output)  # Prints first 20 Fibonacci numbers
```

### Example 2: Batch Validation

```python
from src.batch_runner import run_batch_tests

seeds = [
    "fibonacci with loop",
    "bubble sort",
    "factorial recursion",
    "GCD algorithm",
]
results = run_batch_tests(seeds, temperature=0.3)
# Reports: total, valid, runnable, failed
```

### Example 3: Custom Temperature Control

```python
# Lower temperature = more deterministic, less creative
ir_deterministic = generate_llvm_ir("add two numbers", temperature=0.1)

# Higher temperature = more creative, more varied
ir_creative = generate_llvm_ir("add two numbers", temperature=0.8)
```

## Performance Metrics

| Metric               | Value        | Notes                                  |
| -------------------- | ------------ | -------------------------------------- |
| **Generation Speed** | ~2-4 sec/IR  | Via Groq API (llama-3.3-70b-versatile) |
| **Validation Speed** | ~50ms/IR     | llvm-as + opt --verify                 |
| **Success Rate**     | 85-95%       | Temperature=0.4, LLVM 14 syntax        |
| **Max IR Size**      | ~1500 tokens | Default max_tokens limit               |
| **Timeout (lli)**    | 10 seconds   | Per execution                          |

## Validation Pipeline

```
Generated IR Text
      ↓
   ┌──────────────────────────┐
   │  1. Syntax Check         │
   │  (llvm-as)               │
   └──────────────┬───────────┘
                  ↓
   ┌──────────────────────────┐
   │  2. Semantic Check       │
   │  (opt --verify)          │
   └──────────────┬───────────┘
                  ↓
   ┌──────────────────────────┐
   │  3. Execution            │
   │  (lli)                   │
   └──────────────┬───────────┘
                  ↓
          Valid & Runnable
```

## Troubleshooting

### Issue: "GROQ_API_KEY not set"

**Solution**: Set environment variable or use Colab Secrets

```bash
export GROQ_API_KEY="gsk_..."
```

### Issue: "llvm-as: command not found"

**Solution**: Install LLVM tools

```bash
# Ubuntu/Debian
sudo apt-get install llvm clang

# macOS
brew install llvm
```

### Issue: IR generation fails with "max_tokens exceeded"

**Solution**: Reduce seed complexity or increase max_tokens

```python
generate_llvm_ir(seed, max_tokens=2000)
```

### Issue: "Semantic error" after validation

**Solution**: This indicates an SSA form violation. Try regenerating:

```python
ir = generate_llvm_ir(seed, temperature=0.2)  # Lower T for correctness
```

## API Reference

### `generate_llvm_ir(seed, temperature=0.4, max_tokens=1500) → str`

Generates LLVM IR from a natural language seed.

**Parameters:**

- `seed` (str): Description of desired IR program
- `temperature` (float, 0-1): Generation randomness
- `max_tokens` (int): Maximum output length

**Returns:** Raw LLVM IR text (no markdown)

### `validate_ir(path) → tuple[bool, str, str]`

Validates IR using llvm-as and opt --verify.

**Returns:** (is_valid, status, detailed_message)

### `run_ir(path, timeout=10) → tuple[bool, str]`

Executes IR with lli interpreter.

**Returns:** (success, stdout_stderr_output)

## Related Resources

- [LLVM Language Reference](https://llvm.org/docs/LangRef/)
- [LLVM IR Semantics](https://llvm.org/docs/LanguageReference/#instruction-reference)
- [Groq API Docs](https://console.groq.com/docs)
- [SSA Form](https://en.wikipedia.org/wiki/Static_single_assignment_form)

## License

Educational use. Part of Compiler Design (CD) coursework.

## Author

Generated as part of CD Unit 3 (Compiler Optimization & LLVM) course project.

---

**Last Updated**: May 2026 | **LLVM Version**: 14+ | **Status**: Active Development
