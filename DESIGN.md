# DESIGN: LLVM IR Generator & Validator

## Problem Statement

Generate syntactically and semantically correct LLVM IR code from natural language descriptions using AI, with automated validation and execution feedback.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                   User Interface Layer                          │
│         (Jupyter Notebook + ipywidgets)                         │
└─────────────────────────┬───────────────────────────────────────┘
                          │
        ┌─────────────────┼─────────────────┐
        │                 │                 │
   ┌────▼────┐       ┌────▼────┐      ┌────▼────┐
   │Generator │       │Validator │      │ Runner  │
   │  (Groq)  │       │(llvm-as, │      │  (lli)  │
   └────┬────┘       │opt)       │      └────┬────┘
        │             └────┬────┘            │
        │                  │                 │
        └──────────────────┼─────────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │    Validation & Execution Results   │
        │  (HTML, JSON, Console Output)       │
        └─────────────────────────────────────┘
```

## Design Decisions

### 1. **Choice of AI Model: Groq LLaMA 3.3 70B**

| Aspect      | Why Groq?                                                   |
| ----------- | ----------------------------------------------------------- |
| **Speed**   | Optimized inference via Groq's LLM API (2-4 sec vs 30+ sec) |
| **Cost**    | Pay-per-token, practical for educational use                |
| **Quality** | 70B parameter model → strong code generation                |
| **API**     | Simple REST interface, easy integration                     |

**Alternatives Considered:**

- **OpenAI GPT-4**: Slower, more expensive, but more reliable
- **Local Llama.cpp**: Free, but slow on CPU (~30-60 sec/gen)
- **Claude API**: Better reasoning, but higher cost
- **Fine-tuned Models**: High upfront cost, limited scope

**Decision Rationale:** Groq balances speed, cost, and quality for interactive use.

---

### 2. **Validation Strategy: Two-Stage Pipeline**

```
Stage 1: Syntax Validation (llvm-as)
├── Parses IR text to llvm::Module
├── Checks grammar, operand types, instruction validity
└── Output: .bc (bitcode) file or error

Stage 2: Semantic Verification (opt --verify)
├── Runs SSA form checks
├── Validates dominance properties
├── Verifies function signatures & type consistency
└── Output: Pass/Fail result
```

**Why Two Stages?**

- **llvm-as**: Fast, catches immediate syntactic errors
- **opt --verify**: Comprehensive semantic checks (expensive, worth it)
- **Together**: Catch 95%+ of IR defects before execution

**Alternative:** Run only `llc` (compiler). **Rejected** — less informative errors.

---

### 3. **Prompt Engineering Strategy**

#### System Prompt (Groq Agent Role)

```
You are a senior LLVM IR engineer. Your ONLY output is raw LLVM IR text.
```

**Why**: Forces pure IR output (no markdown, no explanations).

#### Few-Shot Example

Provides reference IR with:

- Proper `target datalayout` and `target triple`
- Typed pointers (LLVM 14 style, no `ptr` keyword)
- SSA form with proper register definitions
- I/O capability via `printf` for observable results

**Advantage**: Model learns from concrete example structure → higher success rate.

#### Temperature Control

- **Low (0.1-0.3)**: Deterministic, safer, suitable for validation testing
- **Medium (0.4)**: Balanced creativity & correctness (default)
- **High (0.7-1.0)**: Diverse outputs, creative (risky for correctness)

---

### 4. **Execution Model: LLVM Interpreter (lli)**

```
Generated IR
    ↓
[llvm-as]  → bitcode
    ↓
[lli]      → execute with JIT
    ↓
stdout/stderr → captured & displayed
```

**Why lli vs. llc?**

- **lli**: Direct interpretation, no compilation step, instant feedback
- **llc**: Generates machine code, requires linking, slower feedback loop

**Timeout**: 10 seconds (prevent infinite loops).

---

### 5. **UI/UX Design: Jupyter Notebook**

**Components:**

1. **Seed Input** (Text field)
2. **Temperature Slider** (0.0 - 1.0)
3. **Control Buttons** (Generate, Validate, Run, Clear)
4. **Output Panes** (IR display, validation result, execution output)
5. **Status Bar** (real-time feedback)

**Why Jupyter?**

- ✅ Interactive, familiar to students
- ✅ Rich HTML/CSS for colored output
- ✅ State persistence across cells
- ✅ Works in Colab (no local install needed)

**Alternatives Considered:**

- **Streamlit**: Cleaner, but overkill for this scope
- **Flask Web App**: More scalable, but deployment complexity
- **CLI Tool**: Fast, but less user-friendly
- **VSCode Extension**: Powerful, but development overhead

---

### 6. **Error Handling & Feedback**

```
User Action → Generator → Validator → Runner
              ↓ error     ↓ error     ↓ error
            HTML msg    HTML msg    HTML msg
              ↓           ↓           ↓
          Status Bar (updates each step)
```

**Error Messages:**

- **Generation**: "❌ Generation failed: [reason]"
- **Validation**: "❌ SYNTAX ERROR" or "❌ SEMANTIC ERROR" + details
- **Execution**: "⏱ Timed out" or "exit [code]: [output]"

---

### 7. **Batch Testing Framework**

```
For each seed:
  1. Generate IR
  2. Validate (syntax + semantic)
  3. Run (if valid)
  4. Collect metrics (pass/fail, exit code, output)

Report: Summary table with seeds, validation status, run output
```

**Metrics Tracked:**

- Total seeds
- Valid IR count
- Successful runs
- Error distribution

---

## Data Flow

### Interactive Mode (Cells 1-4)

```
┌─────────────┐
│  User Input │ ← Seed + Temperature
└──────┬──────┘
       │
       ▼
┌─────────────────────────┐
│ generate_llvm_ir()      │ ← Groq API call
│ Output: .ll text file   │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ User Reviews IR Text    │
│ (displayed in output)   │
└──────┬──────────────────┘
       │
   ◄───┴────────────► [Validate] or [Run] or [Clear]
       │
       ▼
┌─────────────────────────┐
│ validate_ir()           │ ← llvm-as + opt
│ Output: (bool, msg)     │
└──────┬──────────────────┘
       │
       ▼
┌─────────────────────────┐
│ run_ir() [optional]     │ ← lli execution
│ Output: (exit_code, )   │
└─────────────────────────┘
```

### Batch Mode (Cell 5)

```
Seeds[]
  ↓
┌─ For each seed ─────────────────┐
│ 1. generate_llvm_ir()           │
│ 2. validate_ir()                │
│ 3. run_ir() [if valid]          │
│ 4. collect_metrics()            │
└─ End loop ──────────────────────┘
  ↓
Summary HTML Table
  ↓
Display Results
```

---

## API Boundaries

### Public Functions

```python
# Core Generation
def generate_llvm_ir(seed: str, temperature=0.4, max_tokens=1500) -> str

# Validation
def validate_ir(path: str) -> tuple[bool, str, str]

# Execution
def run_ir(path: str, timeout=10) -> tuple[bool, str]

# Batch
def run_batch_tests(seeds: list[str], temperature=0.3) -> dict
```

### Internal Helpers

```python
# Sanitize output
def _clean_ir_output(raw_text) -> str

# HTML escape
def _escape_html(text) -> str

# File I/O
def _write_ir_to_temp(ir_text) -> str
```

---

## Constraints & Assumptions

| Constraint    | Value               | Reason                         |
| ------------- | ------------------- | ------------------------------ |
| LLVM Version  | 14+                 | Modern syntax, typed pointers  |
| IR Tokens     | 1500 max            | Reasonable IR complexity       |
| Timeout       | 10 sec              | Prevent hanging                |
| Temperature   | 0.0-1.0             | Standard LLM range             |
| Pointer Type  | i64\* (x86_64)      | 64-bit architecture assumption |
| Target Triple | x86_64-pc-linux-gnu | Linux/WSL/Colab environment    |

---

## Scalability & Optimization

### Current Limitations

1. Single seed per request (no parallelization in UI)
2. Batch mode processes seeds sequentially
3. No caching of generated IR

### Future Improvements

1. **Parallel Generation**: Run multiple Groq requests concurrently
2. **IR Caching**: Store & reuse previously generated IR for same seeds
3. **Model Fine-Tuning**: Customize Groq model on domain-specific examples
4. **Incremental Validation**: Skip semantic check if syntax fails
5. **Distributed Testing**: Distribute batch runs across nodes

---

## Security Considerations

### Risks

1. **Arbitrary Code Execution**: lli runs generated code
2. **Resource Exhaustion**: Infinite loops consume CPU/memory
3. **API Key Exposure**: Groq key visible in environment

### Mitigations

- ✅ Timeout (10 sec) prevents runaway execution
- ✅ Validation catches most malformed code before execution
- ✅ Environment variable (not hardcoded)
- ⚠️ Sandboxing recommended for production use

---

## Testing Strategy

### Unit Tests

- `test_generator.py`: Mock Groq, verify prompt construction
- `test_validator.py`: Valid & invalid IR files
- `test_runner.py`: IR execution with expected outputs

### Integration Tests

- `test_pipeline.py`: Full generate → validate → run flow
- `test_batch.py`: Multi-seed batch processing

### Test Data

- [testcases/seeds.txt](../testcases/seeds.txt): 10-20 curated test seeds
- [testcases/expected_outputs/](../testcases/expected_outputs/): Reference IR files

---

## Design Trade-offs

| Trade-off                 | Choice               | Rationale                        |
| ------------------------- | -------------------- | -------------------------------- |
| Speed vs. Accuracy        | Moderate (T=0.4)     | Balance for interactive use      |
| Simplicity vs. Generality | Simple pipeline      | Sufficient for educational scope |
| Local vs. API             | API (Groq)           | Speed >> Local inference         |
| Single vs. Multi-modal    | Single task (IR gen) | Focused scope                    |

---

## References

- [LLVM IR Language Reference](https://llvm.org/docs/LangRef/)
- [SSA Form](https://en.wikipedia.org/wiki/Static_single_assignment_form)
- [Prompt Engineering](https://platform.openai.com/docs/guides/prompt-engineering)
- [Large Language Models for Code](https://arxiv.org/abs/2308.12950)

---

**Design Status**: ✅ Stable (v2.0)  
**Last Updated**: May 2026  
**Maintainer**: CD Course Team
