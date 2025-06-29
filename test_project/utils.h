#ifndef UTILS_H
#define UTILS_H

/**
 * 加法函数
 * @param a 第一个操作数
 * @param b 第二个操作数
 * @return 两数之和
 */
int add(int a, int b);

/**
 * 减法函数
 * @param a 第一个操作数
 * @param b 第二个操作数
 * @return 两数之差
 */
int subtract(int a, int b);

/**
 * 乘法函数
 * @param a 第一个操作数
 * @param b 第二个操作数
 * @return 两数之积
 */
int multiply(int a, int b);

/**
 * 判断一个数是否为偶数
 * @param n 要判断的数
 * @return 如果是偶数返回1，否则返回0
 */
int is_even(int n);

#endif /* UTILS_H */ 