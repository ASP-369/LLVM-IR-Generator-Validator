"""
LLVM IR Generation Prompts

System prompts and few-shot examples for Groq LLaMA model.
Designed for high-quality IR generation with minimal hallucination.
Includes an expanded example library for better coverage across
common algorithm categories.
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
- Use `i32*` not `ptr`. Use `i8*` for string pointers.
- Always declare `i32 @printf(i8*, ...)` before using it.
- Format strings must be global `@str` constants with `\\0A\\00` for newline+null.
- Use `align 4` for i32 stack allocations, `align 1` for byte arrays.
- For getelementptr on format strings: `getelementptr inbounds [N x i8], [N x i8]* @str, i64 0, i64 0`.
- Loop pattern: br label %loop_cond, %loop_cond uses phi nodes or reloads via alloca.
- Recursive function pattern: use icmp + br i1 to branch to base case vs recursive case.
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

# ---- Expanded few-shot library (one per algorithm category) ----

EXAMPLE_LOOP = r"""
; Example: Loop with counter (count from 1 to 5)
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)

define i32 @main() {
entry:
  %i = alloca i32, align 4
  store i32 1, i32* %i, align 4
  br label %loop_cond

loop_cond:
  %i_val = load i32, i32* %i, align 4
  %cond = icmp sle i32 %i_val, 5
  br i1 %cond, label %loop_body, label %loop_end

loop_body:
  %fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt, i32 %i_val)
  %next = add nsw i32 %i_val, 1
  store i32 %next, i32* %i, align 4
  br label %loop_cond

loop_end:
  ret i32 0
}
"""

EXAMPLE_FIBONACCI = r"""
; Example: Iterative Fibonacci (N=10)
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)

define i32 @fib(i32 %n) {
entry:
  %a = alloca i32, align 4
  %b = alloca i32, align 4
  %i = alloca i32, align 4
  store i32 0, i32* %a, align 4
  store i32 1, i32* %b, align 4
  store i32 1, i32* %i, align 4
  br label %loop_cond

loop_cond:
  %i_val = load i32, i32* %i, align 4
  %cond = icmp sle i32 %i_val, %n
  br i1 %cond, label %loop_body, label %loop_end

loop_body:
  %a_val = load i32, i32* %a, align 4
  %b_val = load i32, i32* %b, align 4
  %sum = add nsw i32 %a_val, %b_val
  store i32 %b_val, i32* %a, align 4
  store i32 %sum, i32* %b, align 4
  %next = add nsw i32 %i_val, 1
  store i32 %next, i32* %i, align 4
  br label %loop_cond

loop_end:
  %result = load i32, i32* %a, align 4
  ret i32 %result
}

define i32 @main() {
entry:
  %result = call i32 @fib(i32 10)
  %fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt, i32 %result)
  ret i32 0
}
"""

EXAMPLE_RECURSION = r"""
; Example: Recursive factorial (n=5)
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)

define i32 @factorial(i32 %n) {
entry:
  %cond = icmp sle i32 %n, 1
  br i1 %cond, label %base_case, label %recursive_case

base_case:
  ret i32 1

recursive_case:
  %n_minus_1 = sub nsw i32 %n, 1
  %fact_n_minus_1 = call i32 @factorial(i32 %n_minus_1)
  %result = mul nsw i32 %n, %fact_n_minus_1
  ret i32 %result
}

define i32 @main() {
entry:
  %result = call i32 @factorial(i32 5)
  %fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt, i32 %result)
  ret i32 0
}
"""

EXAMPLE_CONDITIONAL = r"""
; Example: Conditional (if-else) with branching
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)

define i32 @max(i32 %a, i32 %b) {
entry:
  %cond = icmp sgt i32 %a, %b
  br i1 %cond, label %then, label %else

then:
  ret i32 %a

else:
  ret i32 %b
}

define i32 @main() {
entry:
  %result = call i32 @max(i32 42, i32 17)
  %fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt, i32 %result)
  ret i32 0
}
"""

EXAMPLE_ARRAY = r"""
; Example: Array sum (5 elements: 10,20,30,40,50)
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@arr = private unnamed_addr constant [5 x i32] [i32 10, i32 20, i32 30, i32 40, i32 50], align 4
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)

define i32 @main() {
entry:
  %sum = alloca i32, align 4
  %i = alloca i32, align 4
  store i32 0, i32* %sum, align 4
  store i32 0, i32* %i, align 4
  br label %loop_cond

loop_cond:
  %i_val = load i32, i32* %i, align 4
  %cond = icmp slt i32 %i_val, 5
  br i1 %cond, label %loop_body, label %loop_end

loop_body:
  %elem_ptr = getelementptr inbounds [5 x i32], [5 x i32]* @arr, i64 0, i32 %i_val
  %elem = load i32, i32* %elem_ptr, align 4
  %sum_val = load i32, i32* %sum, align 4
  %new_sum = add nsw i32 %sum_val, %elem
  store i32 %new_sum, i32* %sum, align 4
  %next = add nsw i32 %i_val, 1
  store i32 %next, i32* %i, align 4
  br label %loop_cond

loop_end:
  %result = load i32, i32* %sum, align 4
  %fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt, i32 %result)
  ret i32 0
}
"""

EXAMPLE_EUCLIDEAN = r"""
; Example: GCD via Euclidean algorithm (48, 18) -> 6
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)

define i32 @gcd(i32 %a, i32 %b) {
entry:
  br label %loop_cond

loop_cond:
  %b_val = phi i32 [%b, %entry], [%rem, %loop_body]
  %a_val = phi i32 [%a, %entry], [%b_val, %loop_body]
  %cond = icmp ne i32 %b_val, 0
  br i1 %cond, label %loop_body, label %loop_end

loop_body:
  %rem = srem i32 %a_val, %b_val
  br label %loop_cond

loop_end:
  ret i32 %a_val
}

define i32 @main() {
entry:
  %result = call i32 @gcd(i32 48, i32 18)
  %fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt, i32 %result)
  ret i32 0
}
"""

EXAMPLE_SORTING = r"""
; Example: Bubble sort on 5-element array
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@arr = private unnamed_addr constant [5 x i32] [i32 5, i32 2, i32 8, i32 1, i32 4], align 4
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)

define void @swap(i32* %p, i32* %q) {
entry:
  %tmp = load i32, i32* %p, align 4
  %qval = load i32, i32* %q, align 4
  store i32 %qval, i32* %p, align 4
  store i32 %tmp, i32* %q, align 4
  ret void
}

define i32 @main() {
entry:
  %i = alloca i32, align 4
  %j = alloca i32, align 4
  %n = alloca i32, align 4
  store i32 0, i32* %i, align 4
  store i32 5, i32* %n, align 4
  br label %outer_cond

outer_cond:
  %i_val = load i32, i32* %i, align 4
  %n_val = load i32, i32* %n, align 4
  %outer_cmp = icmp slt i32 %i_val, 4
  br i1 %outer_cmp, label %outer_body, label %outer_end

outer_body:
  store i32 0, i32* %j, align 4
  br label %inner_cond

inner_cond:
  %j_val = load i32, i32* %j, align 4
  %limit = sub nsw i32 %n_val, %i_val
  %limit_m1 = sub nsw i32 %limit, 1
  %inner_cmp = icmp slt i32 %j_val, %limit_m1
  br i1 %inner_cmp, label %inner_body, label %inner_end

inner_body:
  %jp1 = add nsw i32 %j_val, 1
  %ptr_a = getelementptr inbounds [5 x i32], [5 x i32]* @arr, i64 0, i32 %j_val
  %ptr_b = getelementptr inbounds [5 x i32], [5 x i32]* @arr, i64 0, i32 %jp1
  %a_val = load i32, i32* %ptr_a, align 4
  %b_val = load i32, i32* %ptr_b, align 4
  %cmp = icmp sgt i32 %a_val, %b_val
  br i1 %cmp, label %do_swap, label %skip_swap

do_swap:
  call void @swap(i32* %ptr_a, i32* %ptr_b)
  br label %skip_swap

skip_swap:
  %j_next = add nsw i32 %j_val, 1
  store i32 %j_next, i32* %j, align 4
  br label %inner_cond

inner_end:
  %i_next = add nsw i32 %i_val, 1
  store i32 %i_next, i32* %i, align 4
  br label %outer_cond

outer_end:
  ret i32 0
}
"""

EXAMPLE_STRING = r"""
; Example: String length and print
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"
@msg = private unnamed_addr constant [12 x i8] c"Hello world\00", align 1
@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
@fmt_str = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1
declare i32 @printf(i8* nocapture readonly, ...)
declare i32 @strlen(i8*)

define i32 @main() {
entry:
  %msgptr = getelementptr inbounds [12 x i8], [12 x i8]* @msg, i64 0, i64 0
  %len = call i32 @strlen(i8* %msgptr)
  %fmt_int_ptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt_int_ptr, i32 %len)
  %fmt_str_ptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_str, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt_str_ptr, i8* %msgptr)
  ret i32 0
}
"""

# ---- Keyword-based example library ----

EXAMPLES_LIBRARY = {
    "fibonacci": EXAMPLE_FIBONACCI,
    "fib": EXAMPLE_FIBONACCI,
    "loop": EXAMPLE_LOOP,
    "count": EXAMPLE_LOOP,
    "iter": EXAMPLE_LOOP,
    "factorial": EXAMPLE_RECURSION,
    "recurs": EXAMPLE_RECURSION,
    "recursive": EXAMPLE_RECURSION,
    "max": EXAMPLE_CONDITIONAL,
    "min": EXAMPLE_CONDITIONAL,
    "if": EXAMPLE_CONDITIONAL,
    "else": EXAMPLE_CONDITIONAL,
    "branch": EXAMPLE_CONDITIONAL,
    "conditional": EXAMPLE_CONDITIONAL,
    "compare": EXAMPLE_CONDITIONAL,
    "array": EXAMPLE_ARRAY,
    "sum": EXAMPLE_ARRAY,
    "element": EXAMPLE_ARRAY,
    "gcd": EXAMPLE_EUCLIDEAN,
    "euclidean": EXAMPLE_EUCLIDEAN,
    "bubble": EXAMPLE_SORTING,
    "sort": EXAMPLE_SORTING,
    "swap": EXAMPLE_SORTING,
    "string": EXAMPLE_STRING,
    "strlen": EXAMPLE_STRING,
    "text": EXAMPLE_STRING,
    "character": EXAMPLE_STRING,
    "add": FEW_SHOT_EXAMPLE,
    "addition": FEW_SHOT_EXAMPLE,
    "plus": FEW_SHOT_EXAMPLE,
    "multiply": FEW_SHOT_EXAMPLE,
    "mult": FEW_SHOT_EXAMPLE,
    "subtract": FEW_SHOT_EXAMPLE,
}


def select_template(seed: str) -> str:
    """
    Select the most relevant few-shot example based on seed keywords.

    Scans the seed for keywords present in EXAMPLES_LIBRARY and returns
    the best matching example. Falls back to FEW_SHOT_EXAMPLE.

    Args:
        seed (str): Natural language seed description

    Returns:
        str: Selected example IR (or FEW_SHOT_EXAMPLE if no match)
    """
    seed_lower = seed.lower()

    best_match = None
    best_keyword_len = 0

    for keyword, example in EXAMPLES_LIBRARY.items():
        if keyword in seed_lower and len(keyword) > best_keyword_len:
            best_match = example
            best_keyword_len = len(keyword)

    return best_match if best_match is not None else FEW_SHOT_EXAMPLE


def select_multiple_examples(seed: str, n: int = 2) -> list:
    """
    Select multiple complementary examples for richer few-shot prompting.

    Args:
        seed: Natural language seed
        n: Number of examples to return

    Returns:
        List of example IR strings
    """
    primary = select_template(seed)
    seed_lower = seed.lower()

    candidates = []
    for keyword, example in EXAMPLES_LIBRARY.items():
        if example != primary and keyword in seed_lower:
            candidates.append(example)

    if not candidates:
        for example in [EXAMPLE_LOOP, EXAMPLE_CONDITIONAL, EXAMPLE_ARRAY]:
            if example != primary:
                candidates.append(example)

    return [primary] + candidates[: n - 1]


# ---- Alternative task-specific guidance prompts ----

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
