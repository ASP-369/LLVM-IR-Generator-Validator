target datalayout = "e-m:e-p270:32:32-p271:32:32-p272:64:64-i64:64-f80:128-n8:16:32:64-S128"
target triple = "x86_64-pc-linux-gnu"

define i32 @main() {
entry:
  ; This is an invalid instruction: using a register before defining it
  %1 = add i32 %2, 5
  %2 = add i32 10, 15
  ret i32 %1
}
