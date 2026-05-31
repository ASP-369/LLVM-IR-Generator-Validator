; Fibonacci Sequence (N=10) - Expected Output Reference
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int = private constant [4 x i8] c"%d\0A\00"
declare i32 @printf(i8*, ...)

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
  %i_next = add nsw i32 %i_val, 1
  store i32 %i_next, i32* %i, align 4
  br label %loop_cond

loop_end:
  %result = load i32, i32* %a, align 4
  ret i32 %result
}

define i32 @main() {
entry:
  %result = call i32 @fib(i32 10)
  %fmt_ptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt_ptr, i32 %result)
  ret i32 0
}
