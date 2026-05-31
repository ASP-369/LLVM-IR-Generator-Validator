; Simple Addition - Expected Output Reference
target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int = private constant [4 x i8] c"%d\0A\00"
declare i32 @printf(i8*, ...)

define i32 @add(i32 %a, i32 %b) {
entry:
  %sum = add nsw i32 %a, %b
  ret i32 %sum
}

define i32 @main() {
entry:
  %result = call i32 @add(i32 15, i32 27)
  %fmt_ptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmt_ptr, i32 %result)
  ret i32 0
}
