target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
@fmt_str = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1

declare i32 @printf(i8* nocapture readonly, ...)




define i32 @add(i32 %a, i32 %b) {
entry:
  %result = add nsw i32 %a, %b
  ret i32 %result
}

define i32 @subtract(i32 %a, i32 %b) {
entry:
  %result = sub nsw i32 %a, %b
  ret i32 %result
}

define i32 @compare(i32 %a, i32 %b) {
entry:
  %cmp = icmp sgt i32 %a, %b
  %result = zext i1 %cmp to i32
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
  %sum = call i32 @add(i32 %xval, i32 %yval)
  %diff = call i32 @subtract(i32 %xval, i32 %yval)
  %cmp = call i32 @compare(i32 %xval, i32 %yval)
  %fmtptr = getelementptr inbounds [5 x i8], [5 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmtptr, i32 %sum)
  %fmtptr2 = getelementptr inbounds [5 x i8], [5 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmtptr2, i32 %diff)
  %fmtptr3 = getelementptr inbounds [5 x i8], [5 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmtptr3, i32 %cmp)
  ret i32 0
}