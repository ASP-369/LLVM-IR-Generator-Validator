; GCD Algorithm (48, 18) - Expected Output Reference
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int = private constant [4 x i8] c"%d\0A\00"
declare i32 @printf(i8*, ...)

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
  %fmt_ptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt_ptr, i32 %result)
  ret i32 0
}
