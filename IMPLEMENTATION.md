# IMPLEMENTATION: LLVM IR Details & Technical Notes

## LLVM IR Primer

### What is LLVM IR?

LLVM Intermediate Representation is a low-level assembly-like language that sits between source code and machine code.

**Characteristics:**

- **Human-readable**: Text format (can be printed, debugged, analyzed)
- **SSA-based**: Every variable assigned once (Static Single Assignment)
- **Typed**: Every value has an explicit type
- **Language-neutral**: Generated from C, C++, Rust, Go, etc.

### Basic Syntax

```llvm
; Comments start with semicolon

; Global constants
@message = private constant [6 x i8] c"Hello\00"

; Function declaration
declare i32 @printf(i8*, ...)

; Function definition
define i32 @main() {
entry:
  ; Basic block label
  %0 = call i32 (i8*, ...) @printf(i8* getelementptr inbounds ([6 x i8], [6 x i8]* @message, i64 0, i64 0))
  ret i32 0
}
```

---

## LLVM 14 Features Used

### 1. Typed Pointers (not opaque `ptr`)

```llvm
; LLVM 14 (typed pointers) ✅
define i32 @add(i32 %a, i32 %b) {
  %result = add nsw i32 %a, %b
  ret i32 %result
}

; Old LLVM 15+ (opaque pointers) ❌
; ptr returned, loses type info
```

**Why typed pointers?**

- Explicit type information aids verification
- Better error messages
- Easier for students to understand

---

### 2. Target Datalayout

```llvm
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
```

**Breakdown:**
| Component | Meaning |
|-----------|---------|
| `e` | Little-endian |
| `m:e` | ELF mangling |
| `p270:32:32` | Pointer size 32-bit, align 32 |
| `p271:32:32` | Pointer size 32-bit, align 32 |
| `p272:64:64` | Pointer size 64-bit, align 64 |
| `i64:64` | i64 type: size 64, align 64 |
| `f80:128` | f80 type: size 128, align 128 |
| `n8:16:32:64` | Native integer widths |
| `S128` | Stack align 128 |

**Generated For**: x86_64 Linux (x86_64-pc-linux-gnu)

---

### 3. Target Triple

```llvm
target triple = "x86_64-pc-linux-gnu"
```

| Field        | Value  | Meaning           |
| ------------ | ------ | ----------------- |
| Architecture | x86_64 | 64-bit x86 ISA    |
| Vendor       | pc     | Personal Computer |
| OS           | linux  | Linux kernel      |
| Environment  | gnu    | GNU C library     |

**LLVM Tools Parse This To:**

- Select correct code generation backend
- Choose appropriate calling conventions
- Set default data types

---

## Core IR Constructs

### 1. Basic Types

```llvm
; Integer types
i1      ; boolean
i8      ; byte
i32     ; 32-bit int
i64     ; 64-bit int (used for pointers on x86_64)

; Floating point
float   ; 32-bit IEEE 754
double  ; 64-bit IEEE 754

; Derived types
[4 x i8]        ; Array of 4 bytes
i32*            ; Pointer to i32
{i32, i64, i8*} ; Struct with 3 fields
```

### 2. Memory Operations

```llvm
; Stack allocation
%x = alloca i32, align 4         ; allocate 4 bytes, 4-byte aligned
%arr = alloca [10 x i32], align 4 ; allocate 40 bytes

; Store (write)
store i32 42, i32* %x, align 4   ; write 42 to %x

; Load (read)
%val = load i32, i32* %x, align 4 ; read from %x into %val
```

**Why Alignment?**

- CPU can fetch aligned data faster
- Some SIMD instructions require alignment
- Common alignments: 4 bytes (i32), 8 bytes (i64), 16 bytes (vectors)

### 3. Arithmetic Operations

```llvm
; Addition (no signed/unsigned distinction)
%sum = add i32 %a, %b

; With flags (no wrap, exact)
%sum_nsw = add nsw i32 %a, %b     ; no signed wrap
%sum_nuw = add nuw i32 %a, %b     ; no unsigned wrap

; Subtraction
%diff = sub i32 %a, %b

; Multiplication
%prod = mul i32 %a, %b

; Division (signed vs unsigned)
%quot_s = sdiv i32 %a, %b         ; signed division
%quot_u = udiv i32 %a, %b         ; unsigned division

; Remainder
%rem = srem i32 %a, %b            ; signed remainder
```

**NSw/Nuw Flags**: Enable optimizer to assume no wrap (enables optimizations).

### 4. Bitwise Operations

```llvm
%and_result = and i32 %a, %b      ; bitwise AND
%or_result = or i32 %a, %b        ; bitwise OR
%xor_result = xor i32 %a, %b      ; bitwise XOR
%shl_result = shl i32 %a, 2       ; left shift by 2 bits
%shr_result = lshr i32 %a, 2      ; logical right shift
%sar_result = ashr i32 %a, 2      ; arithmetic right shift
```

### 5. Control Flow

#### Unconditional Branch

```llvm
define void @example() {
entry:
  br label %block_a

block_a:
  ; code here
  br label %block_b

block_b:
  ; code here
  ret void
}
```

#### Conditional Branch (with icmp)

```llvm
entry:
  %cond = icmp slt i32 %x, 10      ; signed less-than
  br i1 %cond, label %if_true, label %if_false

if_true:
  ; code if x < 10
  br label %merge

if_false:
  ; code if x >= 10
  br label %merge

merge:
  ; join point
  ret i32 0
```

**icmp Predicates (signed):**

```llvm
eq   ; equal
ne   ; not equal
slt  ; signed less-than
sle  ; signed less-or-equal
sgt  ; signed greater-than
sge  ; signed greater-or-equal
```

#### Loop with Branches

```llvm
define i32 @loop_example(i32 %n) {
entry:
  %counter = alloca i32, align 4
  store i32 0, i32* %counter, align 4
  br label %loop_header

loop_header:
  %c = load i32, i32* %counter, align 4
  %cond = icmp slt i32 %c, %n
  br i1 %cond, label %loop_body, label %loop_exit

loop_body:
  ; do work
  %c_next = add nsw i32 %c, 1
  store i32 %c_next, i32* %counter, align 4
  br label %loop_header

loop_exit:
  ret i32 0
}
```

### 6. Function Calls

```llvm
; External function declaration
declare i32 @printf(i8* nocapture readonly, ...)

; Function call (no return value)
call void @puts(i8* %str)

; Function call with return value
%result = call i32 @add(i32 15, i32 27)

; Variadic function call
%bytes_written = call i32 (i8*, ...) @printf(i8* %fmt_ptr, i32 42)
```

**Parameters:**

- `nocapture`: Function doesn't store pointer
- `readonly`: Pointed data not modified
- `...`: Variadic arguments (printf)

### 7. Global Variables & Constants

```llvm
; Read-only constant (typically for strings)
@msg = private unnamed_addr constant [13 x i8] c"Hello, World\00"

; Global variable
@counter = global i32 0, align 4

; Use via getelementptr
%ptr = getelementptr inbounds [13 x i8], [13 x i8]* @msg, i64 0, i64 0
call i32 (i8*, ...) @printf(i8* %ptr)
```

**getelementptr (gep):**

```llvm
; Base pointer [type]*, indices...
getelementptr inbounds [13 x i8], [13 x i8]* @msg, i64 0, i64 0
                 ^^^^^^^^^^^^^^^^  ^^^^^^^^^^^^^^^ ^^^^  ^^^^
                 element type      pointer type    i64   i64
```

- First i64 0: Index into array (start of array)
- Second i64 0: Index into i8 (first byte)

---

## Example: Fibonacci Function

```llvm
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

; Compute nth Fibonacci number
define i32 @fib(i32 %n) {
entry:
  %cond = icmp sle i32 %n, 1
  br i1 %cond, label %base_case, label %recursive_case

base_case:
  ret i32 1

recursive_case:
  %n_minus_1 = sub nsw i32 %n, 1
  %n_minus_2 = sub nsw i32 %n, 2

  %fib_n_1 = call i32 @fib(i32 %n_minus_1)
  %fib_n_2 = call i32 @fib(i32 %n_minus_2)

  %result = add nsw i32 %fib_n_1, %fib_n_2
  ret i32 %result
}

@fmt_int = private constant [4 x i8] c"%d\0A\00"
declare i32 @printf(i8*, ...)

define i32 @main() {
entry:
  %fib_10 = call i32 @fib(i32 10)
  %fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt, i32 %fib_10)
  ret i32 0
}
```

**Execution:**

- `./run: fib(10) = 89`

---

## SSA (Static Single Assignment) Form

### Key Property: Each Variable Assigned Once

❌ **Not SSA:**

```llvm
%x = add i32 5, 3     ; assign
%x = mul i32 %x, 2    ; reassign ← violation!
```

✅ **SSA:**

```llvm
%x = add i32 5, 3
%x_mul = mul i32 %x, 2  ; renamed (phi function implicit)
```

### Phi Functions (for control flow merge)

```llvm
if_true:
  %val = add i32 1, 2    ; %val = 3
  br label %merge

if_false:
  %val_2 = add i32 4, 5  ; %val_2 = 9
  br label %merge

merge:
  %result = phi i32 [%val, %if_true], [%val_2, %if_false]
  ; %result = 3 (if came from if_true) OR 9 (if came from if_false)
```

**Why SSA?**

- ✅ Simplifies data flow analysis
- ✅ Enables aggressive optimizations
- ✅ Makes use-def chains trivial to compute

---

## Validation Internals

### What `llvm-as` Checks

1. **Syntax**: Correct tokens, operators, structure
2. **Type consistency**: Operand types match instruction requirements
3. **SSA form**: Each value defined before use
4. **Block structure**: Basic blocks properly formed

**Example Error:**

```
❌ llvm-as error: instruction expects getelementptr return type to be a pointer.
   %val = getelementptr i32, i32 %x, i64 0
              ← expects pointer type, got i32
```

### What `opt --verify` Checks

1. **Dominance**: Definitions dominate uses (def reaches use)
2. **Phi node validity**: All predecessors contribute
3. **Terminator validity**: Blocks end with terminator
4. **Function signature**: Return types, argument types consistent
5. **Calling convention**: Number of args matches declaration

**Example Error:**

```
❌ opt verify error: entry block must be reachable from function entry.
```

---

## Performance Characteristics

### Instruction Costs (Approximate, CPU cycles)

| Instruction | Cost  | Notes                        |
| ----------- | ----- | ---------------------------- |
| `add`       | 1     | Single cycle                 |
| `mul`       | 3-10  | Depends on CPU width         |
| `div`       | 10-40 | Much slower, especially sdiv |
| `load`      | 1-3   | Cache hit: 1, miss: 50+      |
| `store`     | 1-3   | Similar to load              |
| `call`      | 10+   | Function prologue/epilogue   |

**Optimization Implications:**

- Minimize divisions (expensive)
- Hoist loads out of loops
- Inline small functions
- Unroll loops (trade code size for speed)

---

## Common Patterns

### Array Sum

```llvm
define i32 @sum_array(i32* %arr, i32 %size) {
entry:
  %total = alloca i32, align 4
  store i32 0, i32* %total, align 4
  %i = alloca i32, align 4
  store i32 0, i32* %i, align 4
  br label %loop_header

loop_header:
  %i_val = load i32, i32* %i, align 4
  %cond = icmp slt i32 %i_val, %size
  br i1 %cond, label %loop_body, label %loop_end

loop_body:
  %elem_ptr = getelementptr inbounds i32, i32* %arr, i32 %i_val
  %elem = load i32, i32* %elem_ptr, align 4
  %total_val = load i32, i32* %total, align 4
  %new_total = add nsw i32 %total_val, %elem
  store i32 %new_total, i32* %total, align 4

  %i_next = add nsw i32 %i_val, 1
  store i32 %i_next, i32* %i, align 4
  br label %loop_header

loop_end:
  %result = load i32, i32* %total, align 4
  ret i32 %result
}
```

### String Printing

```llvm
@fmt_str = private constant [4 x i8] c"%s\0A\00"
declare i32 @printf(i8*, ...)

%fmt = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_str, i64 0, i64 0
call i32 (i8*, ...) @printf(i8* %fmt, i8* %string_ptr)
```

### Conditional Expression

```llvm
%x = select i1 %cond, i32 %val_true, i32 %val_false
; If %cond is 1: %x = %val_true
; If %cond is 0: %x = %val_false
```

---

## Debugging & Analysis Tools

### 1. View Human-Readable IR

```bash
# From bitcode
llvm-dis file.bc -o file.ll
cat file.ll

# From source (clang -emit-llvm)
clang -emit-llvm -S file.c -o file.ll
```

### 2. Optimize & Show Passes

```bash
opt -O2 -debug file.ll -o optimized.ll
```

### 3. Verify & Show Errors

```bash
opt --verify file.ll
```

### 4. Execute with Debug Output

```bash
lli -debug file.ll
```

### 5. Disassemble to Machine Code

```bash
llc file.ll -o file.s       # IR → assembly
as file.s -o file.o          # assembly → object
ld file.o -o file            # object → executable
./file                         # run
```

---

## Code Generation Pipeline

```
Source Code (C/C++/Rust)
        ↓
   [Frontend: Parse & Type Check]
        ↓
    LLVM IR
        ↓
   [Middle-end: Optimize (mem2reg, inlining, etc.)]
        ↓
    Optimized IR
        ↓
   [Back-end: Select instructions, allocate registers]
        ↓
    Machine Code (x86_64 assembly)
        ↓
   [Assembler & Linker]
        ↓
    Executable Binary
```

**Our Project**: Focuses on IR generation (before middle-end optimizations).

---

## Troubleshooting IR Errors

| Error                                   | Cause                      | Fix                              |
| --------------------------------------- | -------------------------- | -------------------------------- |
| "Instruction expects X to be a pointer" | Type mismatch              | Check operand types              |
| "Instruction requires i1, not i32"      | icmp result type           | Ensure icmp result fed to br     |
| "entry block must be reachable"         | Infinite loop without exit | Add fallthrough/br to exit block |
| "Undefined use of SSA value"            | Use before definition      | Reorder instructions or add phi  |
| "Block does not have a terminator"      | Missing ret/br             | Add terminator at block end      |

---

## References

- [LLVM Language Reference Manual](https://llvm.org/docs/LangRef/)
- [LLVM Programmer's Manual](https://llvm.org/docs/ProgrammersManual/)
- [LLVM 14 Release Notes](https://releases.llvm.org/14.0.0/)
- [Static Single Assignment](https://en.wikipedia.org/wiki/Static_single_assignment_form)

---

**Implementation Version**: 2.0  
**LLVM Target**: 14.0+  
**Last Updated**: May 2026
