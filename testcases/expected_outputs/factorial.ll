; Factorial Using Recursion - Expected Output Reference
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int = private constant [4 x i8] c"%d\0A\00"
declare i32 @printf(i8*, ...)

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
  %fmt_ptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt_ptr, i32 %result)
  ret i32 0
}
