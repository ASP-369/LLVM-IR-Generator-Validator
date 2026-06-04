target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int  = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
@fmt_str  = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1

declare i32 @printf(i8* nocapture readonly, ...)




define i32 @main() {
entry:
  %a = alloca i32, align 4
  %b = alloca i32, align 4
  %i = alloca i32, align 4
  store i32 0, i32* %a, align 4
  store i32 1, i32* %b, align 4
  br label %loop_cond

loop_cond:
  %1 = load i32, i32* %i, align 4
  %2 = icmp slt i32 %1, 10
  br i1 %2, label %loop_body, label %loop_end

loop_body:
  %3 = load i32, i32* %a, align 4
  %4 = load i32, i32* %b, align 4
  %5 = add i32 %3, %4
  store i32 %5, i32* %a, align 4
  store i32 %4, i32* %b, align 4
  %6 = add i32 %1, 1
  store i32 %6, i32* %i, align 4
  br label %loop_cond

loop_end:
  %7 = load i32, i32* %a, align 4
  %8 = getelementptr inbounds [5 x i8], [5 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %8, i32 %7)
  ret i32 0
}