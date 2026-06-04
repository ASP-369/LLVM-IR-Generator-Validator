target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int  = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
@fmt_str  = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1

declare i32 @printf(i8* nocapture readonly, ...)




define i32 @gcd(i32 %a, i32 %b) {
entry:
  %remainder = urem i32 %a, %b
  %cond = icmp eq i32 %remainder, 0
  br i1 %cond, label %return, label %loop

loop:
  %new_a = phi i32 [ %b, %loop ], [ %a, %entry ]
  %new_b = phi i32 [ %remainder, %loop ], [ %b, %entry ]
  %new_remainder = urem i32 %new_a, %new_b
  %new_cond = icmp eq i32 %new_remainder, 0
  br i1 %new_cond, label %return, label %loop

return:
  %result = phi i32 [ %new_remainder, %loop ], [ %b, %entry ]
  ret i32 %result
}

define i32 @main() {
entry:
  %a = alloca i32, align 4
  %b = alloca i32, align 4
  store i32 48, i32* %a, align 4
  store i32 18, i32* %b, align 4
  %aval = load i32, i32* %a, align 4
  %bval = load i32, i32* %b, align 4
  %gcdval = call i32 @gcd(i32 %aval, i32 %bval)
  %fmtptr = getelementptr inbounds [4 x i8], [4 x i8]* @fmt_int, i64 0, i64 0
  call i32 (i8*, ...) @printf(i8* %fmtptr, i32 %gcdval)
  ret i32 0
}