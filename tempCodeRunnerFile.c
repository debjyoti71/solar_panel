#include <stdio.h>
#include <math.h>

int main() {
    int n = 123456789123456789123456789;
    int l = log10(n);
    printf("%d\n", l+1);
    return 0;
}