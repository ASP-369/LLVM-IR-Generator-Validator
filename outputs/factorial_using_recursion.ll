target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int  = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
@fmt_str  = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1

declare i32 @printf(i8* nocapture readonly, ...)




define i32 @factorial(i32 %n) {
entry:
  %0 = icmp eq i32 %n, 0
  br i1 %0, label %base_case, label %recursive_case

base_case:
  ret i32 1

recursive_case:
  %1 = sub nsw i32 %n, 1
  %2 = call i32 @factorial(i32 %1)
  %3 = mul nsw i32 %n, %2
  ret i32 %3
}

define i32 @main() {
entry:
  %x = alloca i32, align 4
  store i32 5, i32* %x, align 4
  %xval = load i32, i32* %x, align 4
  %fmtptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  %call = call i32 @factorial(i32 %xval)
  %fmt_str = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmtptr, i32 %call)
  ret i32 0
}