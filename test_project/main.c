#include <stdio.h>
#include "utils.h"

/**
 * 主函数 - 程序入口
 */
int main() {
    printf("Hello, World!\n");
    
    int a = 5, b = 3;
    printf("%d + %d = %d\n", a, b, add(a, b));
    printf("%d - %d = %d\n", a, b, subtract(a, b));
    printf("%d * %d = %d\n", a, b, multiply(a, b));
    
    if (is_even(a)) {
        printf("%d is even\n", a);
    } else {
        printf("%d is odd\n", a);
    }
    
    return 0;
} 