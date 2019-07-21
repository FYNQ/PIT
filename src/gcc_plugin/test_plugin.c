#include <stdio.h>

static int res;
int resi;
int res2;


struct info{
    int a;
    int b;
    char *c;
};

extern int ggg;
struct info g_info;

int 
add1(int a, int b){
    return a + b;
}

int add2(int a, int b){
    int c = a + b;
    return c;
}


#define max_define(a, b)     \
({                          \
      int n;                \
      n = a + b;            \
})

int main(int argc, char **argv) {

    struct info l_info;

    struct minfo{
        int a;
        int b;
        char *c;
    };
    static int blub_static = 5;
    ggg = 2000;
    struct minfo ldef;
    ldef = (struct minfo) { .a = 1, .b = 0 }; 
    int x;
    int *z;
    int i = 20;
    x = 20;
    l_info.a = 20;
    l_info.b = 20;
    ldef.b = 20;
    x = add2(20,
            30);
    x = max_define(ggg,
            blub_static);

    printf("%d\n", x);
    for (i = 0; i < 20; i++){
        res = add1(l_info.a, l_info.b);
        printf("a + b = %d\n", res);
    }
    return 0;
}

