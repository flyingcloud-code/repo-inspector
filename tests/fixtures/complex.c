#include <stdio.h>
#include <stdlib.h>

int fibonacci(int n) {
    if (n <= 1) return n;
    return fibonacci(n-1) + fibonacci(n-2);
}

void print_sequence(int count) {
    for (int i = 0; i < count; i++) {
        printf("%d ", fibonacci(i));
    }
}

int main() {
    print_sequence(10);
    return 0;
} 