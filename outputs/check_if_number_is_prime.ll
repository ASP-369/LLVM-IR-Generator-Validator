target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

@fmt_int  = private unnamed_addr constant [4 x i8] c"%d\0A\00", align 1
@fmt_str  = private unnamed_addr constant [4 x i8] c"%s\0A\00", align 1
@fmt_prime = private unnamed_addr constant [11 x i8] c"Prime: %d\0A\00", align 1

declare i32 @printf(i8* nocapture readonly, ...)
declare i32 @getchar() nounwind




define i32 @main() {
entry:
  %1 = alloca i32, align 4
  store i32 0, i32* %1, align 4
  %2 = alloca i32, align 4
  store i32 10, i32* %2, align 4
  %3 = load i32, i32* %2, align 4
  %4 = icmp eq i32 %3, 0
  br i1 %4, label %if.then, label %if.else

if.then:
  %5 = load i32, i32* %2, align 4
  %6 = load i32, i32* %1, align 4
  %7 = icmp eq i32 %5, 1
  br i1 %7, label %if.then2, label %if.else2

if.then2:
  %8 = load i32, i32* %1, align 4
  %9 = getelementptr inbounds [12 x i8], [12 x i8]* @fmt_prime, i64 0, i64 0
  %10 = call i32 (i8*, ...) @printf(i8* %9, i32 %8)
  br label %if.end

if.else2:
  %11 = load i32, i32* %1, align 4
  %12 = load i32, i32* %2, align 4
  %13 = sub i32 %12, 1
  store i32 %13, i32* %2, align 4
  %14 = call i32 @getchar() nounwind
  %15 = icmp eq i32 %14, 0
  br i1 %15, label %if.then3, label %if.else3

if.then3:
  %16 = load i32, i32* %2, align 4
  %17 = load i32, i32* %1, align 4
  %18 = icmp eq i32 %16, 1
  br i1 %18, label %if.then4, label %if.else4

if.then4:
  %19 = load i32, i32* %1, align 4
  %20 = getelementptr inbounds [12 x i8], [12 x i8]* @fmt_prime, i64 0, i64 0
  %21 = call i32 (i8*, ...) @printf(i8* %20, i32 %19)
  br label %if.end

if.else4:
  %22 = load i32, i32* %1, align 4
  %23 = load i32, i32* %2, align 4
  %24 = sub i32 %23, 1
  store i32 %24, i32* %2, align 4
  br label %if.else3

if.else3:
  br label %if.else

if.else:
  %25 = load i32, i32* %2, align 4
  %26 = load i32, i32* %1, align 4
  %27 = icmp eq i32 %25, 1
  br i1 %27, label %if.then5, label %if.else5

if.then5:
  %28 = load i32, i32* %1, align 4
  %29 = getelementptr inbounds [5 x i8], [5 x i8]* @fmt_int, i64 0, i64 0
  %30 = call i32 (i8*, ...) @printf(i8* %29, i32 %28)
  br label %if.end

if.else5:
  %31 = load i32, i32* %2, align 4
  %32 = load i32, i32* %1, align 4
  %33 = sub i32 %32, 1
  store i32 %33, i32* %2, align 4
  %34 = call i32 @getchar() nounwind
  %35 = icmp eq i32 %34, 0
  br i1 %35, label %if.then6, label %if.else6

if.then6:
  %36 = load i32, i32* %2, align 4
  %37 = load i32, i32* %1, align 4
  %38 = icmp eq i32 %36, 1
  br i1 %38, label %if.then7, label %if.else7

if.then7:
  %39 = load i32, i32* %1, align 4
  %40 = getelementptr inbounds [5 x i8], [5 x i8]* @fmt_int, i64 0, i64 0
  %41 = call i32 (i8*, ...) @printf(i8* %40, i32 %39)
  br label %if.end

if.else7:
  %42 = load i32, i32* %2, align 4
  %43 = load i32, i32* %1, align 4
  %44 = sub i32 %43, 1
  store i32 %44, i32* %2, align 4
  br label %if.else6

if.else6:
  br label %if.else

if.end:
  ret i32 0
}