"""
LLVM IR Generator & Validator - Gradio UI

Modern web-based interface for the LLVM IR Generator.
Run with: python app.py
Then open the displayed URL in your browser.

Features:
  - 4 tabs: Generate | Batch Test | Compare | About
  - Parameter sliders (temperature, max_tokens, attempts)
  - Side-by-side compare with reference
  - File upload for existing .ll
  - Live metrics and history
"""

import os
import sys
import time
import json
import tempfile
from datetime import datetime
from typing import Optional

import gradio as gr

from src.generator import generate_llvm_ir
from src.validator import validate_ir_text, validate_ir
from src.runner import run_ir_text
from src.correctness import check_correctness, find_reference_for_seed
from src.consensus import generate_with_consensus, generate_with_retry
from src.batch_runner import run_batch_tests
from src.prompts import EXAMPLES_LIBRARY, FEW_SHOT_EXAMPLE


REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
REFERENCES_DIR = os.path.join(REPO_ROOT, "testcases", "expected_outputs")
SEEDS_FILE = os.path.join(REPO_ROOT, "testcases", "seeds.txt")

HISTORY: list = []


# ---- Helper functions ----

def _has_api_key() -> bool:
    return bool(os.environ.get("GROQ_API_KEY", "").strip())


def _read_seeds() -> list:
    if not os.path.exists(SEEDS_FILE):
        return []
    with open(SEEDS_FILE) as f:
        return [line.strip() for line in f if line.strip()]


def _format_validation(ok: bool, status: str, detail: str) -> str:
    icon = "PASS" if ok else "FAIL"
    color = "#10b981" if ok else "#ef4444"
    return (
        f"<div style='padding:12px;border-radius:8px;background:#f8fafc;"
        f"border-left:4px solid {color};margin:8px 0;'>"
        f"<div style='font-weight:600;color:{color};font-size:1.1em;'>"
        f"{icon} {status}</div>"
        f"<pre style='margin:8px 0 0 0;white-space:pre-wrap;font-size:0.85em;"
        f"color:#475569;'>{detail}</pre></div>"
    )


def _format_metrics(metrics: dict) -> str:
    if not metrics:
        return ""
    rows = []
    for k, v in metrics.items():
        if isinstance(v, float):
            v = f"{v:.3f}"
        rows.append(
            f"<div style='display:flex;justify-content:space-between;"
            f"padding:6px 0;border-bottom:1px solid #e2e8f0;'>"
            f"<span style='color:#64748b;'>{k}</span>"
            f"<span style='font-weight:600;color:#0f172a;'>{v}</span></div>"
        )
    return (
        "<div style='background:#f1f5f9;padding:16px;border-radius:8px;"
        "font-family:ui-monospace,monospace;font-size:0.9em;'>"
        + "".join(rows)
        + "</div>"
    )


def _format_output(success: bool, output: str) -> str:
    icon = "PASS" if success else "FAIL"
    color = "#10b981" if success else "#ef4444"
    return (
        f"<div style='padding:12px;border-radius:8px;background:#f8fafc;"
        f"border-left:4px solid {color};margin:8px 0;'>"
        f"<div style='font-weight:600;color:{color};'>{icon} Execution</div>"
        f"<pre style='margin:8px 0 0 0;white-space:pre-wrap;font-size:0.85em;"
        f"color:#475569;'>{(output or '(no output)')[:1000]}</pre></div>"
    )


# ---- Tab 1: Generate ----

def do_generate(
    seed: str,
    temperature: float,
    max_tokens: int,
    use_retry: bool,
    max_attempts: int,
    progress=gr.Progress(),
) -> tuple:
    """Generate IR, validate, run, check correctness."""
    if not seed or not seed.strip():
        return "ERROR: seed is empty", "", "", "", "", None
    if not _has_api_key():
        return (
            "ERROR: GROQ_API_KEY not set. Run: set GROQ_API_KEY=your_key",
            "", "", "", "", None,
        )

    started = time.time()
    metrics = {}

    progress(0.1, desc="Generating IR...")
    if use_retry:
        rc = generate_with_retry(
            seed, max_attempts=int(max_attempts), temperature=float(temperature)
        )
        ir = rc.get("ir") or ""
        metrics["attempts"] = rc.get("attempts", 0)
        metrics["first_attempt_success"] = rc.get("attempts", 0) == 1 and rc.get("success")
        history_md_lines = []
        for h in rc.get("history", []):
            tag = "OK" if h["is_valid"] else f"FAIL: {(h.get('error') or '')[:80]}"
            history_md_lines.append(f"- **Attempt {h['attempt']}**: {tag}")
        history_md = "\n".join(history_md_lines) or "No attempts recorded"
    else:
        try:
            progress(0.3, desc="Calling Groq API...")
            ir = generate_llvm_ir(seed, temperature=float(temperature), max_tokens=int(max_tokens))
            metrics["attempts"] = 1
            history_md = "- **Attempt 1**: Single-shot generation"
        except Exception as e:
            return f"Generation error: {e}", "", "", "", history_md or "", None

    metrics["gen_time_sec"] = round(time.time() - started, 2)

    if not ir:
        return "ERROR: no IR generated", "", "", metrics_html(metrics), history_md, None

    progress(0.6, desc="Validating IR (llvm-as + opt --verify)...")
    val_start = time.time()
    ok, status, detail = validate_ir_text(ir, require_main=True)
    metrics["val_time_sec"] = round(time.time() - val_start, 3)
    metrics["valid"] = ok
    metrics["validation_status"] = status
    val_html = _format_validation(ok, status, detail)

    run_html = ""
    output_text = ""
    if ok:
        progress(0.8, desc="Executing IR with lli...")
        run_start = time.time()
        try:
            success, output = run_ir_text(ir, timeout=10)
            metrics["run_time_sec"] = round(time.time() - run_start, 3)
            metrics["executable"] = success
            run_html = _format_output(success, output)
            output_text = output or ""
            if success:
                ref_path = find_reference_for_seed(seed, REFERENCES_DIR)
                if ref_path:
                    progress(0.9, desc="Checking output correctness vs reference...")
                    ck = check_correctness(ir, ref_path, timeout=10)
                    metrics["output_correct"] = ck.get("correct", False)
                    if ck.get("ref_output"):
                        metrics["ref_output"] = ck["ref_output"][:60]
                    if ck.get("gen_output"):
                        metrics["gen_output"] = ck["gen_output"][:60]
        except Exception as e:
            run_html = f"<div style='color:#ef4444;'>Execution error: {e}</div>"
            metrics["executable"] = False

    progress(1.0, desc="Done")

    HISTORY.append({
        "timestamp": datetime.now().strftime("%H:%M:%S"),
        "seed": seed,
        "ir_len": len(ir),
        "valid": ok,
        "metrics": metrics,
    })

    download_path = None
    if ir:
        dl_dir = os.path.join(REPO_ROOT, "outputs")
        os.makedirs(dl_dir, exist_ok=True)
        safe_seed = "".join(c if c.isalnum() else "_" for c in seed)[:40]
        download_path = os.path.join(dl_dir, f"{safe_seed}.ll")
        with open(download_path, "w") as f:
            f.write(ir)

    return (
        ir,
        val_html,
        run_html,
        metrics_html(metrics),
        history_md,
        download_path,
    )


def metrics_html(m: dict) -> str:
    return _format_metrics(m)


# ---- Tab 2: Batch Test ----

def do_batch(
    temperature: float,
    timeout: int,
    mode: str,
    n_attempts: int,
    use_seeds_file: bool,
    custom_seeds: str,
    progress=gr.Progress(),
) -> tuple:
    if use_seeds_file:
        seeds = _read_seeds()
    else:
        seeds = [s.strip() for s in custom_seeds.splitlines() if s.strip()]

    if not seeds:
        return "ERROR: no seeds provided", "", ""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        out_file = f.name

    progress(0, desc="Starting batch tests...")
    results = run_batch_tests(
        seeds=seeds,
        temperature=float(temperature),
        timeout=int(timeout),
        output_file=out_file,
        mode=mode,
        max_attempts=int(n_attempts),
        n_consensus=int(n_attempts),
    )

    progress(1.0, desc="Done")

    summary = (
        f"Total: {results['total']}\n"
        f"Valid (semantic): {results['valid_semantic']}/{results['total']}\n"
        f"Runnable: {results['runnable']}/{results['total']}\n"
        f"Output correct: {results['correct']}/{results['runnable']}\n"
        f"First-attempt rate: {results.get('first_attempt_rate', 'n/a')}%\n"
        f"Avg attempts: {results.get('avg_attempts', 'n/a')}\n"
        f"Failed: {results['failed']}/{results['total']}\n"
        f"\nPer-category:\n"
        + "\n".join(
            f"  {cat}: {s['passed']}/{s['total']} pass, {s['correct']}/{s['total']} correct"
            for cat, s in results.get("per_category", {}).items()
        )
    )

    rows = []
    for r in results["results"]:
        rows.append([
            r.get("seed", "")[:50],
            r.get("status", ""),
            r.get("attempts", 1),
            r.get("gen_time", 0),
            "OK" if r.get("output_correct") else ("--" if r.get("output_correct") is None else "X"),
            (r.get("error") or "")[:80],
        ])

    return summary, results, out_file


# ---- Tab 3: Compare ----

def do_compare(seed: str, temperature: float) -> tuple:
    ref_path = find_reference_for_seed(seed, REFERENCES_DIR)
    if not ref_path:
        return "No reference file found for this seed.", "", "", ""

    with open(ref_path) as f:
        ref_ir = f.read()

    if not _has_api_key():
        return "GROQ_API_KEY not set", ref_ir, "", ""

    try:
        gen_ir = generate_llvm_ir(seed, temperature=float(temperature))
    except Exception as e:
        return f"Generation error: {e}", ref_ir, "", ""

    ok, status, detail = validate_ir_text(gen_ir, require_main=True)
    val_html = _format_validation(ok, status, detail)

    diff_lines = []
    ref_lines = ref_ir.splitlines()
    gen_lines = gen_ir.splitlines()
    max_len = max(len(ref_lines), len(gen_lines))
    for i in range(max_len):
        r = ref_lines[i] if i < len(ref_lines) else ""
        g = gen_lines[i] if i < len(gen_lines) else ""
        marker = " " if r == g else "*"
        diff_lines.append(f"{marker} {i+1:3d} | {r[:60]:60s} | {g[:60]}")
    diff_text = "\n".join(diff_lines[:200])

    return f"Reference: {os.path.basename(ref_path)} | Generated: {len(gen_lines)} lines", ref_ir, gen_ir, diff_text


# ---- File upload handler ----

def do_upload_validate(file) -> tuple:
    if file is None:
        return "No file uploaded", ""
    try:
        if hasattr(file, "name"):
            path = file.name
        else:
            path = file
        ok, status, detail = validate_ir(path)
        return _format_validation(ok, status, detail), ""
    except Exception as e:
        return f"Error: {e}", ""


# ---- Build UI ----

CUSTOM_CSS = """
.container { max-width: 1400px; margin: auto; }
.header { text-align: center; padding: 20px 0; }
.metric-box { background: #f1f5f9; padding: 12px; border-radius: 8px; }
.code-block { font-family: ui-monospace, "Cascadia Code", "Source Code Pro", monospace; }
"""

EXAMPLE_SEEDS = [
    "fibonacci sequence with loops",
    "factorial using recursion",
    "calculate GCD using Euclidean algorithm",
    "bubble sort algorithm on array",
    "add two numbers",
    "sum array elements",
    "check if number is prime",
    "compute maximum element in array",
]


def build_ui() -> gr.Blocks:
    custom_theme = gr.themes.Soft(
        primary_hue="indigo",
        secondary_hue="blue",
        neutral_hue="slate",
        font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    ).set(
        body_background_fill="linear-gradient(to bottom right, #0f172a, #1e1b4b)",
        body_background_fill_dark="linear-gradient(to bottom right, #0f172a, #1e1b4b)",
        block_background_fill="rgba(30, 41, 59, 0.7)",
        block_background_fill_dark="rgba(30, 41, 59, 0.7)",
        block_border_width="1px",
        block_border_color="rgba(255, 255, 255, 0.1)",
        block_border_color_dark="rgba(255, 255, 255, 0.1)",
        block_shadow="0 8px 32px 0 rgba(0, 0, 0, 0.3)",
        button_primary_background_fill="linear-gradient(to right, #4f46e5, #7c3aed)",
        button_primary_background_fill_dark="linear-gradient(to right, #4f46e5, #7c3aed)",
        button_primary_border_color="transparent",
        button_primary_border_color_dark="transparent",
        button_primary_text_color="white",
        button_primary_text_color_dark="white",
        input_background_fill="rgba(15, 23, 42, 0.6)",
        input_background_fill_dark="rgba(15, 23, 42, 0.6)",
        input_border_color="rgba(255, 255, 255, 0.2)",
    )

    with gr.Blocks(title="LLVM IR Generator", theme=custom_theme) as demo:
        gr.HTML("""
        <div class="header">
            <h1>LLVM IR Generator & Validator</h1>
            <p>Generate, validate, and execute LLVM IR from natural language</p>
        </div>
        """)

        if not _has_api_key():
            gr.HTML("""
            <div style="padding:14px;background:#fee2e2;border:1px solid #fca5a5;
                        border-radius:8px;color:#991b1b;margin:10px 0;">
                <strong>GROQ_API_KEY not set.</strong>
                Set it via <code>set GROQ_API_KEY=your_key</code> (Windows) or
                <code>export GROQ_API_KEY=your_key</code> (Linux/macOS), then restart.
            </div>
            """)

        with gr.Tabs():
            # ---- TAB 1: GENERATE ----
            with gr.Tab("Generate"):
                with gr.Row():
                    with gr.Column(scale=1):
                        gr.Markdown("### Input")
                        seed_in = gr.Dropdown(
                            choices=EXAMPLE_SEEDS,
                            value=EXAMPLE_SEEDS[0],
                            allow_custom_value=True,
                            label="Choose a program to generate (Seed)",
                        )
                        with gr.Accordion("Advanced settings", open=False):
                            temp_slider = gr.Slider(
                                minimum=0.0, maximum=1.0, step=0.05,
                                value=0.3, label="Temperature",
                            )
                            tokens_slider = gr.Slider(
                                minimum=500, maximum=3000, step=100,
                                value=1500, label="Max tokens",
                            )
                            use_retry = gr.Checkbox(
                                label="Use retry with self-correction",
                                value=True,
                            )
                            attempts_slider = gr.Slider(
                                minimum=1, maximum=5, step=1,
                                value=3, label="Max attempts",
                            )
                        gen_btn = gr.Button("Generate IR", variant="primary", size="lg")

                    with gr.Column(scale=2):
                        gr.Markdown("### Generated LLVM IR")
                        ir_out = gr.Code(
                            label="LLVM IR (click to copy)",
                            language="cpp",
                            lines=18,
                            interactive=True,
                        )
                        with gr.Row():
                            download_btn = gr.DownloadButton(
                                "Download .ll",
                                variant="secondary",
                                size="sm",
                            )
                        with gr.Row():
                            val_html = gr.HTML()
                            run_html = gr.HTML()
                        with gr.Row():
                            with gr.Column():
                                gr.Markdown("#### Metrics")
                                metrics_panel = gr.HTML()
                            with gr.Column():
                                gr.Markdown("#### Generation history")
                                history_md = gr.Markdown()

                gen_btn.click(
                    fn=do_generate,
                    inputs=[seed_in, temp_slider, tokens_slider, use_retry, attempts_slider],
                    outputs=[ir_out, val_html, run_html, metrics_panel, history_md, download_btn],
                )

            # ---- TAB 2: BATCH TEST ----
            with gr.Tab("Batch Test"):
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("### Configuration")
                        use_seeds_file = gr.Checkbox(
                            label="Use seeds from testcases/seeds.txt",
                            value=True,
                        )
                        custom_seeds_in = gr.Textbox(
                            label="Custom seeds (one per line)",
                            placeholder="fibonacci with loops\nfactorial recursion\n...",
                            lines=5,
                            visible=False,
                        )
                        batch_temp = gr.Slider(0.0, 1.0, 0.3, step=0.05, label="Temperature")
                        batch_timeout = gr.Slider(2, 60, 10, step=1, label="Timeout (sec)")
                        batch_mode = gr.Radio(
                            choices=["single", "retry", "consensus"],
                            value="retry",
                            label="Generation mode",
                        )
                        batch_attempts = gr.Slider(1, 5, 3, step=1, label="Attempts / candidates")
                        batch_btn = gr.Button("Run batch tests", variant="primary")

                    with gr.Column(scale=2):
                        gr.Markdown("### Summary")
                        batch_summary = gr.Textbox(label="Results", lines=10, interactive=False)
                        gr.Markdown("### Per-seed results")
                        batch_table = gr.Dataframe(
                            headers=["Seed", "Status", "Attempts", "Gen Time", "Output", "Error"],
                            interactive=False,
                        )
                        batch_json = gr.File(label="Download full results JSON")

                use_seeds_file.change(
                    fn=lambda x: gr.update(visible=not x),
                    inputs=[use_seeds_file],
                    outputs=[custom_seeds_in],
                )
                batch_btn.click(
                    fn=do_batch,
                    inputs=[batch_temp, batch_timeout, batch_mode, batch_attempts, use_seeds_file, custom_seeds_in],
                    outputs=[batch_summary, batch_table, batch_json],
                )

            # ---- TAB 3: COMPARE ----
            with gr.Tab("Compare with Reference"):
                with gr.Row():
                    cmp_seed = gr.Dropdown(
                        choices=EXAMPLE_SEEDS,
                        value=EXAMPLE_SEEDS[0],
                        allow_custom_value=True,
                        label="Seed to compare",
                    )
                    cmp_temp = gr.Slider(0.0, 1.0, 0.3, step=0.05, label="Temperature")
                    cmp_btn = gr.Button("Compare", variant="primary")
                cmp_status = gr.Markdown()
                with gr.Row():
                    with gr.Column():
                        gr.Markdown("#### Reference IR (golden)")
                        cmp_ref = gr.Code(language="cpp", lines=20, interactive=False)
                    with gr.Column():
                        gr.Markdown("#### Generated IR")
                        cmp_gen = gr.Code(language="cpp", lines=20, interactive=False)
                gr.Markdown("#### Line-by-line diff ( * = different )")
                cmp_diff = gr.Textbox(label="Diff", lines=15, interactive=False)
                cmp_btn.click(
                    fn=do_compare,
                    inputs=[cmp_seed, cmp_temp],
                    outputs=[cmp_status, cmp_ref, cmp_gen, cmp_diff],
                )

            # ---- TAB 4: VALIDATE FILE ----
            with gr.Tab("Validate File"):
                gr.Markdown("### Upload an existing .ll file for validation")
                upload = gr.File(label="Upload .ll file", file_types=[".ll", ".txt"])
                upload_btn = gr.Button("Validate", variant="primary")
                upload_result = gr.HTML()
                upload_btn.click(
                    fn=do_upload_validate,
                    inputs=[upload],
                    outputs=[upload_result, gr.HTML()],
                )

            # ---- TAB 5: ABOUT ----
            with gr.Tab("About"):
                gr.Markdown("""
                # About

                **LLVM IR Generator & Validator v2.1**

                An advanced, AI-powered tool that automatically generates valid, optimized LLVM IR from natural language descriptions. It validates the output using `llvm-as` and `opt`, executes it locally using `lli`, and checks output against golden references.

                ## Powered by NVIDIA NIM (moonshotai/kimi-k2.6) 🚀
                This version has been completely upgraded to run on **NVIDIA's API** using the powerful `kimi-k2.6` model for superior code generation capabilities.

                ## What's New in v2.1
                - **Premium Glassmorphism UI**: A complete overhaul of the user interface featuring beautiful typography and dark-mode gradients.
                - **Auto-Correction Engine**: Uses a multi-attempt retry loop that reads LLVM compiler errors and feeds them back to the model for self-correction.
                - **Robust Post-Processing**: Includes custom Python algorithms that automatically clean up LLVM syntax quirks (e.g. hoisting globals, re-ordering phi nodes, renaming duplicate registers, fixing C-string null-terminators).
                
                ## Requirements
                - **LLVM 14+** (llvm-as, opt, lli on PATH)
                - **Python 3.8+**
                - **NVIDIA_API_KEY** environment variable
                - **gradio** framework

                *Built for compiler enthusiasts, students, and system engineers.*

                ## Quick Install

                ```bash
                pip install groq gradio
                # Linux:   sudo apt install llvm clang
                # macOS:   brew install llvm
                ```

                ## Features

                - **3-column workspace**: input | IR | validation
                - **Retry with self-correction**: feeds LLVM errors back to LLM
                - **Consensus voting**: generates N candidates, picks best
                - **Output correctness check**: runs reference + generated, compares
                - **Side-by-side compare**: line-by-line diff vs golden reference
                - **Per-category accuracy** in batch results
                - **File upload**: validate existing .ll files

                ## Architecture

                ```
                src/
                  generator.py       # Groq LLaMA IR generation
                  validator.py       # Syntax + semantic check
                  runner.py          # lli execution
                  correctness.py     # Output diff vs reference
                  consensus.py       # Multi-attempt + self-correction
                  batch_runner.py    # Batch testing with metrics
                  prompts.py         # 8+ few-shot examples
                app.py              # This Gradio UI
                ```
                """)

    return demo


if __name__ == "__main__":
    demo = build_ui()
    print("=" * 60)
    print("LLVM IR Generator & Validator - Gradio UI")
    print("=" * 60)
    if not _has_api_key():
        print("WARNING: GROQ_API_KEY not set. Set it before generating.")
    print("Starting server...")
    demo.launch(server_name="0.0.0.0", server_port=7860, share=False, inbrowser=True)
