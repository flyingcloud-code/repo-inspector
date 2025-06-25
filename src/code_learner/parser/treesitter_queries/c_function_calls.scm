;; Tree-sitter C 函数调用查询 (Story 2.1.3)
;; 捕获各种形式的函数调用表达式

; 直接调用 foo();
((call_expression
  function: (identifier) @callee.direct)
  @call)

; 结构体成员调用 obj->foo(); 或 obj.foo();
((call_expression
  function: (field_expression) @callee.member)
  @call)

; 函数指针调用 (*fp)();
((call_expression
  function: (pointer_expression) @callee.pointer)
  @call) 