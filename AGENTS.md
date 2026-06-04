# AGENTS.md — Project context for AI agents / future sessions

## What this is
LLVM IR Generator & Validator v2.1 — Gradio UI that uses Groq LLaMA to generate
LLVM IR from natural-language seeds, then validates with `llvm-as` + `opt` and
runs with `lli`. Entry point: `app.py`.

## Quick start
```bash
export GROQ_API_KEY="gsk_..."          # or put in .env (see below)
python3 app.py                          # → http://localhost:7860
```

Offline smoke test of the LLVM toolchain:
```bash
cat <<'EOF' > /tmp/t.ll
define i32 @main() { ret i32 0 }
EOF
llvm-as /tmp/t.ll -o /tmp/t.bc && lli /tmp/t.bc   # → 0
```

## Environment / secrets
- API key is read in `src/generator.py:14` via `os.environ.get("GROQ_API_KEY", "")`
- `app.py:42-58` adds a tiny `_load_env_file()` that reads `.env` and `.env.local`
  from the project root **before** the `from src.generator import ...` line
  (the Groq client is constructed at module-import time, so the env var must
  be set before any `src.*` import).
- `.env.example` is the template; `.env` and `.env.local` are gitignored.
- **Never commit the real key.** The user already shared theirs in chat —
  rotate at https://console.groq.com/keys when the demo is done.

## Pinned working versions (Ubuntu 24.04, Python 3.12)
The fresh-install matrix on this system:

| Package | Version | Why pinned |
|---|---|---|
| `gradio` | `4.44.1` | project code uses Gradio 4 API (`gr.Code(language="llvm")`, `theme=` in `Blocks`) |
| `gradio-client` | `1.3.0` | required by gradio 4.44.1; patched in-place (see below) |
| `huggingface_hub` | `<0.25` | Gradio 4 imports `HfFolder` which was removed in 1.0 |
| `starlette` | `>=0.40,<0.42` | Starlette 1.x changed `TemplateResponse` signature, breaks Gradio 4 routes |
| `fastapi` | `>=0.115,<0.118` | matches `starlette<0.42` |
| `jinja2` | `3.1.2` (system) | works; newer 3.1.5+ changes `LRUCache` keys |
| `groq` | `1.4.0` | latest |
| LLVM | `llvm-18` | `~/.local/bin/{llvm-as,opt,lli,clang}` symlinks to `-18` variants |

Install in one go:
```bash
pip3 install --break-system-packages -r requirements.txt \
  'gradio==4.44.1' 'gradio-client==1.3.0' 'huggingface_hub<0.25' \
  'starlette>=0.40,<0.42' 'fastapi>=0.115,<0.118'
```

## Patches applied in-tree (do not undo)

### `app.py`
- Added `_load_env_file()` (lines 42-58) — no new dep
- Reordered so `.env` is loaded **before** the `from src.generator import ...` line
- `app.py:159` — error display in history: 80 → 400 chars
- `app.py:412,498,501` — `language="llvm"` → `language="cpp"` (Gradio 4.44 dropped `llvm`)
- `app.py:586` — `inbrowser=True` → `inbrowser=False` (headless-safe)

### `src/validator.py:199` and `src/batch_runner.py:478`
- `opt -verify` → `opt -passes=verify` (LLVM 15+ new pass manager)
- Falls back to `-verify` if the new PM syntax isn't recognized

### `src/generator.py:21` and `src/consensus.py:194`
- `model="llama-3.3-70b-versatile"` → `os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")`
- Default model is now overridable via `GROQ_MODEL` env var

### `~/.local/lib/python3.12/site-packages/gradio_client/utils.py`
Two in-place patches to handle non-dict schemas (booleans slipping in):
- Line ~862 `get_type()`: added `if not isinstance(schema, dict): return {}` guard
- Line ~900 `_json_schema_to_python_type()`: same guard, plus
  `desc = schema.get("description"); if isinstance(desc, str) and "json" in desc: ...`

These will be lost if `gradio-client` is reinstalled. Re-apply or vendor the
file if that happens.

### `~/.local/bin/{llvm-as,opt,lli,clang}`
- Symlinks to `/usr/bin/{llvm-as,opt,lli}-18` and `/usr/bin/clang` so the
  unversioned names work without `sudo apt install llvm`.

## Known issues / gotchas
1. **Groq free tier quota**: `llama-3.3-70b-versatile` is **100K TPD**.
   `llama-3.1-8b-instant` is **~500K TPD**. If you see 429, switch via
   `GROQ_MODEL` in `.env`.
2. **LLM parameter-pointer confusion**: the LLM sometimes writes
   `load i32, i32* %n` where `%n` is a function parameter (an SSA value,
   not a pointer). Lower temperature to 0.1 or accept that retry will
   usually fix it on attempt 2.
3. **`language="llvm"`**: not supported in Gradio 4.44 or 6.x. We use
   `"cpp"` for syntax highlighting; LLVM IR is C-like so it looks fine.
4. **Browser autoload**: `inbrowser=True` fails in headless / remote sessions.
   Keep it `False`; user opens the URL manually.
5. **Case-sensitivity**: `GROQ_API_key` ≠ `GROQ_API_KEY` on Linux. Watch
   the casing when echoing/exporting.

## Project structure
```
app.py                      # Gradio web UI (entry point)
build.sh                    # Original install script (Linux/macOS)
run.sh                      # Notebook launcher
requirements.txt            # Loose pins (gradio>=4.0.0 etc.)
src/
  generator.py              # Groq LLaMA IR generation
  validator.py              # llvm-as + opt --passes=verify
  runner.py                 # lli execution
  correctness.py            # Output diff vs golden reference
  consensus.py              # Multi-attempt + self-correction
  batch_runner.py           # Batch testing
  prompts.py                # 8+ few-shot examples
testcases/
  seeds.txt                 # 15 test seeds
  expected_outputs/*.ll     # Golden reference IRs
  results.json              # Sample results
.env.example                # Template
.env                        # Real key (gitignored)
```

## Common commands
```bash
# Run UI
python3 app.py

# Run unit tests
python3 -m pytest test_app.py -v 2>/dev/null || python3 test_app.py

# Batch test (uses API quota)
python3 -c "from src import run_batch_tests; print(run_batch_tests(open('testcases/seeds.txt').read().splitlines(), mode='retry', max_attempts=3, output_file='testcases/results.json'))"

# Programmatic use
python3 -c "from src import generate_with_retry; r = generate_with_retry('fibonacci sequence with loops', max_attempts=3); print(f'attempts={r[\"attempts\"]} success={r[\"success\"]}')"
```

## Things to NOT change
- Don't `pip install gradio` without the `<5` cap (Gradio 6 will re-break it)
- Don't remove the `.env`-before-import ordering in `app.py`
- Don't reinstall `gradio-client` without re-applying the two `utils.py` patches
- Don't commit `.env`
