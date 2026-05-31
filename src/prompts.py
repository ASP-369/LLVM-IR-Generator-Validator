"""
LLVM IR Generation Prompts

System prompts and few-shot examples for Groq LLaMA model.
Designed for high-quality IR generation with minimal hallucination.
"""

# System prompt: Role definition for the model
SYSTEM_PROMPT = """\
You are a senior LLVM IR engineer. Your ONLY output is raw LLVM IR text.

Strict rules:
- Use LLVM 14 syntax exclusively.
- Always include `target datalayout` and `target triple`.
- Use typed pointers (no opaque pointers — avoid `ptr` keyword).
- All SSA registers must be defined before use.
- Every basic block must end with a terminator (ret, br, unreachable).
- Do NOT emit markdown, backticks, or any prose. Pure IR only.
"""

# Few-shot example: Reference IR demonstrating best practices
FEW_SHOT_EXAMPLE = r"""
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int  = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
@fmt_str  = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1

declare i32 @printf(i8* nocapture readonly, ...)

define i32 @add(i32 %a, i32 %b) {
entry:
  %result = add nsw i32 %a, %b
  ret i32 %result
}

define i32 @main() {
entry:
  %x = alloca i32, align 4
  %y = alloca i32, align 4
  store i32 15, i32* %x, align 4
  store i32 27, i32* %y, align 4
  %xval = load i32, i32* %x, align 4
  %yval = load i32, i32* %y, align 4
  %sum  = call i32 @add(i32 %xval, i32 %yval)
  %fmtptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmtptr, i32 %sum)
  ret i32 0
}
"""

# Alternative prompts for specific use cases

FIBONACCI_TEMPLATE = """\
Generate LLVM IR to compute the Nth Fibonacci number using iteration (not recursion).
Include:
- A loop structure with icmp and conditional branching
- Memory allocation (alloca) for loop counter and result
- Load/store operations
- Proper SSA form with renamed variables
- Printf to output the result
"""

SORTING_TEMPLATE = """\
Generate LLVM IR to implement a simple sorting algorithm (bubble sort or selection sort).
Include:
- Nested loop structure
- Array allocation and indexing (getelementptr)
- Comparison and conditional branching
- Memory operations (load/store)
- Function to perform swap/comparison
"""

RECURSION_TEMPLATE = """\
Generate LLVM IR for a recursive function (factorial or fibonacci).
Include:
- Base case with immediate return
- Recursive case with self-call
- Proper SSA form with renamed registers
- Stack allocation for local variables
- Return value merging (phi nodes if needed)
"""

STRING_MANIPULATION_TEMPLATE = """\
Generate LLVM IR for string operations (length, concatenation, reversal).
Include:
- Global string constants
- Character iteration loops
- Memory pointer arithmetic (getelementptr)
- Printf for output
- Proper null-terminator handling
"""

# Helper function to select template based on keyword
def select_template(seed: str) -> str:
    """
    Select appropriate few-shot template based on seed keywords.

    Args:
        seed (str): Natural language seed description

    Returns:
        str: Appropriate template or default FEW_SHOT_EXAMPLE
    """
    seed_lower = seed.lower()

    if any(word in seed_lower for word in ["fibonacci", "fib"]):
        return FEW_SHOT_EXAMPLE + "\n\n; Additional guidance:\n" + FIBONACCI_TEMPLATE

    if any(word in seed_lower for word in ["sort", "bubble", "quick", "merge"]):
        return FEW_SHOT_EXAMPLE + "\n\n; Additional guidance:\n" + SORTING_TEMPLATE

    if any(word in seed_lower for word in ["recursive", "recursion", "factorial"]):
        return FEW_SHOT_EXAMPLE + "\n\n; Additional guidance:\n" + RECURSION_TEMPLATE

    if any(word in seed_lower for word in ["string", "text", "character", "concat"]):
        return FEW_SHOT_EXAMPLE + "\n\n; Additional guidance:\n" + STRING_MANIPULATION_TEMPLATE

    return FEW_SHOT_EXAMPLE
