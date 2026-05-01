# General C++ Learning Guide — Complete Reference

> **Scope:** C++ from first principles through modern C++17
> **Purpose:** Foundation knowledge required before specialising in embedded/automotive C++
> **Compiler standard:** C++11 / C++14 / C++17

---

## Table of Contents

1. [History & Compilation Model](#1-history--compilation-model)
2. [Variables, Types & Literals](#2-variables-types--literals)
3. [Operators](#3-operators)
4. [Control Flow](#4-control-flow)
5. [Functions](#5-functions)
6. [Pointers & References](#6-pointers--references)
7. [Arrays & Strings](#7-arrays--strings)
8. [Structs & Unions](#8-structs--unions)
9. [Classes & OOP](#9-classes--oop)
10. [Inheritance & Polymorphism](#10-inheritance--polymorphism)
11. [Templates](#11-templates)
12. [The Standard Library (STL)](#12-the-standard-library-stl)
13. [Memory Management](#13-memory-management)
14. [Modern C++11/14/17 Features](#14-modern-c111417-features)
15. [File I/O](#15-file-io)
16. [Exception Handling](#16-exception-handling)
17. [Namespaces](#17-namespaces)
18. [Preprocessor](#18-preprocessor)
19. [Concurrency (std::thread)](#19-concurrency-stdthread)
20. [Best Practices & Common Pitfalls](#20-best-practices--common-pitfalls)

---

## 1. History & Compilation Model

### Brief History

```
1972  → C language created at Bell Labs (Ritchie, Thompson)
1979  → "C with Classes" — Bjarne Stroustrup's extension
1985  → C++ officially named, first commercial release
1998  → C++98 — first ISO standard
2003  → C++03 — bug-fix revision
2011  → C++11 — modern C++ begins (lambda, auto, move semantics, threads)
2014  → C++14 — small improvements, generic lambdas
2017  → C++17 — structured bindings, if constexpr, std::optional, std::variant
2020  → C++20 — concepts, ranges, coroutines, modules
2023  → C++23 — std::expected, std::print, stack_trace
```

### Compilation Pipeline

```
Source file (main.cpp)
        │
        ▼
  Preprocessor (cpp)
  • Expand #include, #define, #ifdef
  • Produces translation unit (pure C++)
        │
        ▼
  Compiler (g++/clang++)
  • Lexing → Parsing → Semantic Analysis
  • AST → IR → Optimisation → Machine code
  • Produces object file (main.o)
        │
        ▼
  Linker (ld)
  • Combines .o files + libraries
  • Resolves symbol references
  • Produces executable (a.out / main.exe)

Common flags:
  g++ -std=c++17 -Wall -Wextra -O2 -o program main.cpp
```

### Hello World Dissected

```cpp
#include <iostream>    // include standard I/O header (preprocessor directive)

int main() {           // entry point — returns int to OS
    std::cout          // standard output stream object
        << "Hello"     // stream insertion operator
        << std::endl;  // newline + flush (or use '\n' — faster)
    return 0;          // 0 = success
}
```

---

## 2. Variables, Types & Literals

### Fundamental Types

```cpp
// Boolean
bool flag = true;        // true or false — 1 byte

// Characters
char c = 'A';            // 1 byte, may be signed or unsigned
signed char sc = -5;
unsigned char uc = 200U;
wchar_t wc = L'Ω';       // wide character (2 or 4 bytes)
char16_t u16 = u'\u03A9'; // Unicode (C++11)
char32_t u32 = U'\U000003A9';

// Integers
short s  = -1000;         // at least 16 bits
int   i  = -1000000;      // at least 16 bits (usually 32)
long  l  = -1000000L;     // at least 32 bits
long long ll = -9000000LL; // at least 64 bits
// Unsigned variants: unsigned short, unsigned int, unsigned long, ...

// Floating point
float  f = 3.14f;          // 32-bit IEEE 754 (~7 sig. digits)
double d = 3.14159265358;  // 64-bit IEEE 754 (~15 sig. digits)
long double ld = 3.14L;    // 80 or 128 bits (platform dependent)

// Void
void* generic_ptr = nullptr;  // pointer to unspecified type
```

### Literals

```cpp
// Integer literals
int dec  = 255;       // decimal
int oct  = 0377;      // octal (prefix 0)
int hex  = 0xFF;      // hexadecimal (prefix 0x)
int bin  = 0b11111111; // binary (C++14, prefix 0b)

// Digit separator (C++14)
uint32_t million = 1'000'000U;
uint32_t address = 0x4002'0000UL;

// Floating
double pi  = 3.14159;
float  pi2 = 3.14159f;    // f suffix = float
double sci = 1.5e10;      // scientific notation 1.5 × 10^10

// Character
char newline  = '\n';
char tab      = '\t';
char null_chr = '\0';
char hex_chr  = '\x41';   // 'A'

// String
const char* str = "Hello";          // C-string (null terminated)
std::string s   = "Hello";          // std::string object
std::string raw = R"(line1\nline2)"; // raw string (C++11) — \n is literal
```

### Type Sizes on Common Platforms

```
Type          | Size (x86-64 Linux/Win) | Range
--------------|-------------------------|-------------------------------
bool          | 1 byte                  | true / false
char          | 1 byte                  | -128 to 127
unsigned char | 1 byte                  | 0 to 255
short         | 2 bytes                 | -32,768 to 32,767
int           | 4 bytes                 | -2.1B to 2.1B
long          | 8 bytes (Linux)         | -(2^63) to 2^63 - 1
              | 4 bytes (Windows)       |
long long     | 8 bytes                 | -(2^63) to 2^63 - 1
float         | 4 bytes                 | ~1.2e-38 to ~3.4e+38
double        | 8 bytes                 | ~2.2e-308 to ~1.8e+308
pointer       | 8 bytes (64-bit)        | any address

Use sizeof() to check on your platform:
std::cout << sizeof(int) << '\n';    // prints 4
```

### `auto` — Type Deduction (C++11)

```cpp
auto x = 42;           // int
auto y = 3.14;         // double
auto z = 3.14f;        // float
auto s = "hello";      // const char*
auto str = std::string{"hello"}; // std::string

// In for loops
std::vector<int> v = {1, 2, 3};
for (auto elem : v) {}          // elem is int (copy)
for (auto& elem : v) {}         // elem is int& (reference)
for (const auto& elem : v) {}   // elem is const int& (read-only)

// auto with initializer_list
auto il = {1, 2, 3};  // std::initializer_list<int>
```

### `decltype` — Type of Expression

```cpp
int a = 5;
decltype(a) b = 10;      // b is int
decltype(a + 0.0) c;     // c is double (type of a+0.0)

// Useful in templates (C++14: auto return)
auto add(int x, int y) -> decltype(x + y) {
    return x + y;
}
```

---

## 3. Operators

### Arithmetic

```cpp
int a = 10, b = 3;
int sum   = a + b;   // 13
int diff  = a - b;   // 7
int prod  = a * b;   // 30
int quot  = a / b;   // 3 (integer division — truncates toward zero)
int rem   = a % b;   // 1 (modulo — sign follows dividend in C++)

// Compound assignment
a += 5;   // a = a + 5
a -= 2;   // a = a - 2
a *= 3;   // a = a * 3
a /= 4;   // a = a / 4
a %= 3;   // a = a % 3

// Increment / decrement
++a;  // pre-increment: increment THEN use — preferred
a++;  // post-increment: use THEN increment — creates copy internally
--a;  // pre-decrement
a--;  // post-decrement
```

### Relational & Logical

```cpp
bool r1 = (5 == 5);   // true   — equality
bool r2 = (5 != 4);   // true   — inequality
bool r3 = (5 > 3);    // true   — greater than
bool r4 = (5 < 3);    // false  — less than
bool r5 = (5 >= 5);   // true   — greater than or equal
bool r6 = (5 <= 4);   // false  — less than or equal

bool l1 = (true && false); // false — AND
bool l2 = (true || false); // true  — OR
bool l3 = !true;           // false — NOT

// Short-circuit evaluation:
// In (A && B): if A is false, B is NOT evaluated
// In (A || B): if A is true,  B is NOT evaluated
```

### Bitwise

```cpp
uint8_t a = 0b10110011;  // 179
uint8_t b = 0b11001010;  // 202

uint8_t bitAnd  = a & b;   // 0b10000010 = 130  (AND — both 1)
uint8_t bitOr   = a | b;   // 0b11111011 = 251  (OR — either 1)
uint8_t bitXor  = a ^ b;   // 0b01111001 =  121 (XOR — exactly one 1)
uint8_t bitNot  = ~a;      // 0b01001100 =  76  (NOT — flip all)
uint8_t lshift  = a << 1;  // 0b01100110 = 102  (left shift 1 = multiply by 2)
uint8_t rshift  = a >> 1;  // 0b01011001 =  89  (right shift 1 = divide by 2)

// Common patterns:
// Set bit n:    value |=  (1U << n);
// Clear bit n:  value &= ~(1U << n);
// Toggle bit n: value ^=  (1U << n);
// Test bit n:   (value >> n) & 1U
```

### Ternary Operator

```cpp
int x = 10;
int abs_x = (x >= 0) ? x : -x;  // if x>=0 then x else -x

// Can be nested (but avoid for readability)
std::string grade = (score >= 90) ? "A" :
                    (score >= 80) ? "B" :
                    (score >= 70) ? "C" : "F";
```

### Operator Precedence (high to low, simplified)

```
Precedence | Operators
-----------|------------------------------------------
1 (high)   | :: (scope)
2          | () [] . -> ++ -- (postfix)
3          | ++ -- (prefix) + - ! ~ * & (unary)
4          | .* ->* (pointer-to-member)
5          | * / %
6          | + -
7          | << >>
8          | < <= > >=
9          | == !=
10         | &
11         | ^
12         | |
13         | &&
14         | ||
15         | ?: (ternary)
16         | = += -= *= /= ...
17 (low)   | , (comma)
```

---

## 4. Control Flow

### `if` / `else if` / `else`

```cpp
int score = 75;

if (score >= 90) {
    std::cout << "A\n";
} else if (score >= 80) {
    std::cout << "B\n";
} else if (score >= 70) {
    std::cout << "C\n";
} else {
    std::cout << "F\n";
}

// C++17: if with initializer
if (int result = computeResult(); result > 0) {
    use(result);
}
```

### `switch`

```cpp
char grade = 'B';
switch (grade) {
    case 'A':
        std::cout << "Excellent\n";
        break;
    case 'B':
    case 'C':                  // fall-through (both handled same way)
        std::cout << "Good\n";
        break;
    default:
        std::cout << "Unknown\n";
        break;
}

// switch on enum class (C++11)
enum class Color { Red, Green, Blue };
Color c = Color::Green;
switch (c) {
    case Color::Red:   /* ... */ break;
    case Color::Green: /* ... */ break;
    case Color::Blue:  /* ... */ break;
}
```

### `for` Loop

```cpp
// Classic for
for (int i = 0; i < 10; ++i) {
    std::cout << i << ' ';
}

// Range-based for (C++11)
std::vector<int> v = {1, 2, 3, 4, 5};
for (int x : v) {           // copy each element
    std::cout << x << ' ';
}
for (const int& x : v) {    // const reference — no copy
    std::cout << x << ' ';
}
for (auto& x : v) {          // auto reference — can modify
    x *= 2;
}

// Infinite loop
for (;;) {
    if (done) break;
}
```

### `while` & `do-while`

```cpp
// while: condition checked before body
int i = 0;
while (i < 5) {
    std::cout << i++ << ' ';
}

// do-while: body executes at least once
int n;
do {
    std::cout << "Enter positive number: ";
    std::cin >> n;
} while (n <= 0);
```

### `break`, `continue`, `goto`

```cpp
// break — exit loop or switch
for (int i = 0; i < 10; ++i) {
    if (i == 5) break;    // exits loop when i==5
}

// continue — skip rest of loop body, next iteration
for (int i = 0; i < 10; ++i) {
    if (i % 2 == 0) continue;   // skip even
    std::cout << i << ' ';       // prints 1 3 5 7 9
}

// goto — generally avoid, except in C-style cleanup patterns
// Forbidden in MISRA / automotive code
```

---

## 5. Functions

### Function Declaration & Definition

```cpp
// Declaration (prototype) — tells compiler signature
int add(int a, int b);

// Definition — body
int add(int a, int b) {
    return a + b;
}

// Can declare and define together if defined before first use
double square(double x) {
    return x * x;
}
```

### Parameters

```cpp
// Pass by value — function gets a copy
void byValue(int x) { x = 100; }  // caller's x unchanged

// Pass by reference — function works on caller's variable
void byRef(int& x) { x = 100; }   // caller's x IS changed

// Pass by const reference — read-only, no copy overhead
void byConstRef(const std::string& s) {
    std::cout << s;
}

// Pass by pointer
void byPointer(int* p) {
    if (p != nullptr) *p = 100;
}

// Default arguments
void connect(std::string host, int port = 8080, bool tls = false) {}
connect("localhost");           // port=8080, tls=false
connect("server.com", 443, true);
```

### Return Values

```cpp
// Return single value
int multiply(int a, int b) { return a * b; }

// Return multiple values (struct)
struct MinMax { int min; int max; };
MinMax findMinMax(const std::vector<int>& v) {
    return {*std::min_element(v.begin(), v.end()),
            *std::max_element(v.begin(), v.end())};
}
auto [mn, mx] = findMinMax({3, 1, 4, 1, 5, 9}); // C++17 structured binding

// Return by reference — caller can modify
int& getElement(std::vector<int>& v, int i) { return v[i]; }
getElement(v, 0) = 99;   // modifies v[0]

// Return optional (C++17)
#include <optional>
std::optional<int> safeDivide(int a, int b) {
    if (b == 0) return std::nullopt;
    return a / b;
}
```

### Function Overloading

```cpp
// Same name, different parameter types/count
void print(int x)    { std::cout << "int: "    << x << '\n'; }
void print(double x) { std::cout << "double: " << x << '\n'; }
void print(std::string s) { std::cout << "string: " << s << '\n'; }

print(42);          // calls print(int)
print(3.14);        // calls print(double)
print("hello");     // calls print(std::string)

// Rules:
// - Return type alone does NOT distinguish overloads
// - Compiler chooses best match via implicit conversion ranking
```

### Inline Functions

```cpp
// Suggest compiler replace call with function body (avoids call overhead)
inline int clamp(int v, int lo, int hi) {
    return v < lo ? lo : (v > hi ? hi : v);
}

// Modern constexpr implies inline
constexpr int square(int x) { return x * x; }
```

### Recursive Functions

```cpp
// Factorial — classic recursion
long long factorial(int n) {
    if (n <= 1) return 1;           // base case
    return n * factorial(n - 1);   // recursive call
}

// Fibonacci with memoization
#include <unordered_map>
long long fib(int n, std::unordered_map<int,long long>& memo) {
    if (n <= 1) return n;
    if (memo.count(n)) return memo[n];
    return memo[n] = fib(n-1, memo) + fib(n-2, memo);
}
```

### Lambda Expressions (C++11)

```cpp
// Syntax: [capture](params) -> return_type { body }

// Simple lambda
auto square = [](int x) { return x * x; };
std::cout << square(5);   // 25

// Capture by value
int base = 10;
auto addBase = [base](int x) { return x + base; };  // base copied at definition

// Capture by reference
int counter = 0;
auto increment = [&counter]() { ++counter; };
increment(); increment();
std::cout << counter;   // 2

// Capture all by value: [=], by reference: [&]
auto f = [=](int x) { return x + base; };  // captures all locals by value

// Mutable lambda — modify captured by-value
auto counting = [n = 0]() mutable { return ++n; };

// Generic lambda (C++14)
auto maxOf = [](auto a, auto b) { return a > b ? a : b; };
maxOf(3, 5);         // int
maxOf(3.0, 5.0);     // double

// Immediately invoked
int result = [](int x, int y) { return x + y; }(3, 4);   // 7
```

---

## 6. Pointers & References

### Pointers Fundamentals

```cpp
int value = 42;
int* ptr = &value;      // ptr holds ADDRESS of value

std::cout << ptr;       // prints address (e.g., 0x7ffe3a8c)
std::cout << *ptr;      // dereference: prints 42

*ptr = 100;             // modifies value through pointer
std::cout << value;     // 100

// Pointer arithmetic
int arr[5] = {10, 20, 30, 40, 50};
int* p = arr;           // points to arr[0]
std::cout << *p;        // 10
++p;                    // now points to arr[1]
std::cout << *p;        // 20
std::cout << *(p + 2);  // 40 (arr[3])

// NULL / nullptr
int* null_ptr = nullptr;   // C++11, preferred over NULL or 0
if (null_ptr != nullptr) { *null_ptr = 5; }  // safe check
```

### Pointer to Pointer

```cpp
int x = 5;
int* p = &x;
int** pp = &p;    // pointer to pointer to int

std::cout << **pp;   // 5 (dereference twice)
```

### const Pointer Combinations

```cpp
int a = 10, b = 20;

// Pointer to const int — can move pointer, cannot change pointed value
const int* p1 = &a;
p1 = &b;       // OK — pointer can change
// *p1 = 30;   // ERROR — value is const

// Const pointer to int — cannot move pointer, can change value
int* const p2 = &a;
*p2 = 30;      // OK — value can change
// p2 = &b;    // ERROR — pointer is const

// Const pointer to const int — neither can change
const int* const p3 = &a;
// *p3 = 30;   // ERROR
// p3 = &b;    // ERROR

// Memory trick: read right-to-left
// "p3 is a const pointer to const int"
```

### References

```cpp
int x = 10;
int& ref = x;    // ref is an alias for x — same memory

ref = 20;
std::cout << x;  // 20 — x was changed through ref

// References vs pointers:
// ✓ References cannot be null
// ✓ References cannot be reseated (always refer to same object)
// ✓ No dereference syntax needed
// ✗ Cannot do arithmetic on references
// ✗ Cannot have reference to reference

// Rvalue reference (C++11) — binds to temporaries
int&& rref = 42;     // rref binds to temporary value 42
```

### Smart Pointers (C++11)

```cpp
#include <memory>

// unique_ptr — sole ownership, auto-deleted when out of scope
std::unique_ptr<int> uptr = std::make_unique<int>(42);
std::cout << *uptr;      // 42
// No need to delete — destructor handles it
// uptr2 = uptr;         // ERROR — cannot copy, only move
auto uptr2 = std::move(uptr);  // transfer ownership

// shared_ptr — shared ownership, reference counted
std::shared_ptr<int> sp1 = std::make_shared<int>(100);
std::shared_ptr<int> sp2 = sp1;    // both own the int
std::cout << sp1.use_count();  // 2
sp1.reset();                   // sp1 releases, count drops to 1
// int auto-deleted when last shared_ptr is destroyed

// weak_ptr — observe shared_ptr without owning (breaks circular refs)
std::weak_ptr<int> wp = sp2;
if (auto locked = wp.lock()) {    // lock() returns shared_ptr if still alive
    std::cout << *locked;
}
```

---

## 7. Arrays & Strings

### C-Style Arrays

```cpp
// Declaration
int arr[5];                  // 5 ints, uninitialised
int arr2[5] = {1, 2, 3};     // first 3 set, rest 0
int arr3[]  = {1, 2, 3, 4};  // size deduced = 4

// Access — 0-based indexing
arr[0] = 10;
arr[4] = 50;

// Iterate
for (int i = 0; i < 5; ++i) {
    arr[i] *= 2;
}

// Array decays to pointer when passed to function
void printArray(const int* arr, int size) {
    for (int i = 0; i < size; ++i) std::cout << arr[i] << ' ';
}

// sizeof array
int a[10];
int count = sizeof(a) / sizeof(a[0]);   // 10

// 2D array
int matrix[3][4];
matrix[1][2] = 99;
```

### `std::array` (C++11) — Preferred

```cpp
#include <array>

std::array<int, 5> arr = {1, 2, 3, 4, 5};

// Bounds checking
arr.at(10);     // throws std::out_of_range
arr[10];        // undefined behaviour (no check)

// Size
std::cout << arr.size();    // 5

// Iteration
for (auto& x : arr) x *= 2;

// Algorithms work directly
std::sort(arr.begin(), arr.end());
```

### `std::vector` — Dynamic Array

```cpp
#include <vector>

std::vector<int> v;          // empty
std::vector<int> v2(5, 0);   // 5 zeros
std::vector<int> v3 = {1, 2, 3};

// Add/remove
v3.push_back(4);             // add to end
v3.pop_back();               // remove from end
v3.insert(v3.begin() + 1, 99);  // insert 99 at index 1
v3.erase(v3.begin() + 1);   // erase at index 1

std::cout << v3.size();      // current elements
std::cout << v3.capacity();  // allocated capacity (may be > size)
v3.reserve(100);             // pre-allocate for 100 elements

// Access
v3[0];          // no bounds check
v3.at(0);       // bounds-checked
v3.front();     // first element
v3.back();      // last element
v3.data();      // raw pointer to underlying array
```

### C-Style Strings

```cpp
#include <cstring>

const char* hello = "Hello";       // string literal (read-only)
char buffer[20] = "Hello";         // mutable copy

std::strlen(buffer);               // 5 (not counting '\0')
std::strcpy(dest, src);            // copy (use strncpy for safety)
std::strcat(dest, src);            // concatenate
std::strcmp("abc", "abd");         // negative (a < first diff b)
std::strncpy(dest, src, n);        // safe copy up to n chars
```

### `std::string` — Preferred

```cpp
#include <string>

std::string s = "Hello";
std::string s2("World");
std::string s3(5, 'x');     // "xxxxx"

// Operations
s += " World";              // append
s.append("!!!");
s.length();                 // 11
s.size();                   // same as length
s.empty();                  // false

// Access
s[0];          // 'H' — no bounds check
s.at(0);       // bounds-checked
s.front();     // first char
s.back();      // last char

// Search
s.find("World");         // returns index or std::string::npos
s.find('o');
s.rfind('o');             // search from right
s.contains("Hello");     // C++23

// Substrings
s.substr(0, 5);           // "Hello" (pos, length)

// Comparison
s == "Hello World!!!";    // true
s.compare("abc");         // <0, 0, >0

// Conversion
std::to_string(42);       // int → "42"
std::to_string(3.14);     // double → "3.140000"
int n = std::stoi("42");
double d = std::stod("3.14");

// Split (no built-in — common snippet)
std::string line = "a,b,c";
std::stringstream ss(line);
std::string token;
while (std::getline(ss, token, ',')) {
    std::cout << token << '\n';
}
```

---

## 8. Structs & Unions

### Structs

```cpp
// Plain Old Data (POD) struct
struct Point {
    double x;
    double y;
};

// Initialisation
Point p1;              // members uninitialized
Point p2 = {1.0, 2.0};
Point p3{3.0, 4.0};   // uniform initialization (C++11)
Point p4{};            // zero-initialised

// Access
p2.x = 5.0;

// Aggregate initialization
struct Rectangle {
    Point topLeft;
    Point bottomRight;
    std::string label;
};
Rectangle r{{0,0}, {10,5}, "Box"};

// Designated initializers (C++20)
Point dp{.x = 1.0, .y = 2.0};

// Struct with methods
struct Circle {
    double radius;
    double area() const { return 3.14159 * radius * radius; }
};
```

### Unions

```cpp
// All members share same memory — only one member valid at a time
union Data {
    int   iVal;
    float fVal;
    char  cArr[4];
};

Data d;
d.iVal = 255;
std::cout << d.iVal;    // 255
d.fVal = 3.14f;         // now fVal is active — iVal is garbage

// Use case: type-punning (reading float bytes as int)
union FloatBytes {
    float f;
    uint32_t bits;
};
FloatBytes fb;
fb.f = 1.0f;
std::cout << std::hex << fb.bits;  // 3f800000 (IEEE 754)

// MISRA / safety: avoid unions (undefined which member is active)
// Prefer std::variant (C++17) in modern code
```

---

## 9. Classes & OOP

### Class Basics

```cpp
class BankAccount {
public:                          // accessible from outside
    // Constructor
    BankAccount(std::string owner, double balance)
        : m_owner(owner), m_balance(balance) {}

    // Destructor
    ~BankAccount() {
        std::cout << "Account " << m_owner << " destroyed\n";
    }

    // Methods
    void deposit(double amount) {
        if (amount > 0) m_balance += amount;
    }

    bool withdraw(double amount) {
        if (amount > m_balance) return false;
        m_balance -= amount;
        return true;
    }

    double getBalance() const { return m_balance; }   // const method
    const std::string& getOwner() const { return m_owner; }

private:                         // accessible only within class
    std::string m_owner;
    double      m_balance;
};

// Usage
BankAccount acc("Alice", 1000.0);
acc.deposit(500.0);
acc.withdraw(200.0);
std::cout << acc.getBalance();   // 1300.0
```

### Constructors — All Types

```cpp
class Widget {
public:
    // Default constructor
    Widget() : m_value(0) {}

    // Parameterised constructor
    explicit Widget(int v) : m_value(v) {}
    // explicit: prevents implicit conversion Widget w = 5; (forbidden with explicit)

    // Copy constructor
    Widget(const Widget& other) : m_value(other.m_value) {}

    // Move constructor (C++11)
    Widget(Widget&& other) noexcept : m_value(other.m_value) {
        other.m_value = 0;
    }

    // Copy assignment operator
    Widget& operator=(const Widget& other) {
        if (this != &other) {
            m_value = other.m_value;
        }
        return *this;
    }

    // Move assignment operator (C++11)
    Widget& operator=(Widget&& other) noexcept {
        if (this != &other) {
            m_value = other.m_value;
            other.m_value = 0;
        }
        return *this;
    }

    // Destructor
    ~Widget() = default;

private:
    int m_value;
};

// Rule of Five (C++11): if you define any of destructor, copy ctor,
// copy assignment, move ctor, move assignment → define all five.
// Rule of Zero: if your class only holds well-behaved members (std::string,
// std::vector, smart ptrs), don't define any — compiler-generated are fine.
```

### Member Initializer List

```cpp
class Engine {
public:
    // Preferred: initializer list (faster — direct construction)
    Engine(int cylinders, double displacement)
        : m_cylinders(cylinders),        // order MUST match declaration order
          m_displacement(displacement),
          m_running(false) {}

    // BAD: assignment in body (default-constructs THEN assigns)
    Engine(int c, double d) {
        m_cylinders   = c;    // already default-constructed above
        m_displacement = d;
    }

private:
    int    m_cylinders;
    double m_displacement;
    bool   m_running;
};
```

### Operator Overloading

```cpp
class Vector2D {
public:
    Vector2D(double x, double y) : m_x(x), m_y(y) {}

    // Arithmetic operators
    Vector2D operator+(const Vector2D& o) const { return {m_x+o.m_x, m_y+o.m_y}; }
    Vector2D operator-(const Vector2D& o) const { return {m_x-o.m_x, m_y-o.m_y}; }
    Vector2D operator*(double scalar)     const { return {m_x*scalar, m_y*scalar}; }

    // Compound assignment
    Vector2D& operator+=(const Vector2D& o) { m_x+=o.m_x; m_y+=o.m_y; return *this; }

    // Comparison
    bool operator==(const Vector2D& o) const { return m_x==o.m_x && m_y==o.m_y; }
    bool operator!=(const Vector2D& o) const { return !(*this == o); }

    // Subscript
    double& operator[](int i) { return i == 0 ? m_x : m_y; }

    // Stream output (non-member friend)
    friend std::ostream& operator<<(std::ostream& os, const Vector2D& v) {
        return os << "(" << v.m_x << ", " << v.m_y << ")";
    }

    double length() const { return std::sqrt(m_x*m_x + m_y*m_y); }

private:
    double m_x, m_y;
};

Vector2D a{1.0, 2.0}, b{3.0, 4.0};
auto c = a + b;          // (4, 6)
std::cout << c << '\n';  // uses << overload
```

### `static` Members & Methods

```cpp
class Counter {
public:
    Counter() { ++s_count; }
    ~Counter() { --s_count; }

    static int getCount() { return s_count; }  // can be called without object
    // static methods cannot access non-static members (no 'this' pointer)

private:
    static int s_count;    // shared across ALL instances
};
int Counter::s_count = 0;  // definition OUTSIDE class

Counter c1, c2, c3;
std::cout << Counter::getCount();  // 3
```

### `friend` Functions & Classes

```cpp
class Matrix {
private:
    double data[4][4];

    // friend function can access private members
    friend double trace(const Matrix& m);

    // friend class can access all private members
    friend class MatrixPrinter;
};

double trace(const Matrix& m) {
    return m.data[0][0] + m.data[1][1] + m.data[2][2] + m.data[3][3];
}
```

---

## 10. Inheritance & Polymorphism

### Basic Inheritance

```cpp
// Base class
class Animal {
public:
    Animal(std::string name) : m_name(name) {}
    virtual ~Animal() = default;        // virtual destructor — REQUIRED for polymorphism

    virtual void speak() const {         // virtual — derived can override
        std::cout << m_name << " makes a sound\n";
    }

    std::string getName() const { return m_name; }

protected:                               // accessible in derived classes
    std::string m_name;
};

// Derived class
class Dog : public Animal {
public:
    Dog(std::string name, std::string breed)
        : Animal(name), m_breed(breed) {}   // call base constructor

    void speak() const override {           // override (C++11 keyword — compile-time check)
        std::cout << m_name << " barks!\n";
    }

    void fetch() const { std::cout << m_name << " fetches!\n"; }

private:
    std::string m_breed;
};

class Cat : public Animal {
public:
    Cat(std::string name) : Animal(name) {}
    void speak() const override {
        std::cout << m_name << " meows!\n";
    }
};

// Polymorphism via pointer/reference to base
Animal* animals[] = { new Dog("Rex", "Lab"), new Cat("Whiskers") };
for (auto* a : animals) {
    a->speak();     // dynamic dispatch — calls correct derived speak()
}
```

### Abstract Classes & Pure Virtual

```cpp
// Abstract class — cannot be instantiated, defines interface
class Shape {
public:
    virtual ~Shape() = default;
    virtual double area()      const = 0;   // pure virtual — MUST override
    virtual double perimeter() const = 0;
    virtual void   draw()      const = 0;

    // Non-virtual utility method
    void printInfo() const {
        std::cout << "Area: " << area() << " Perimeter: " << perimeter() << '\n';
    }
};

class Circle : public Shape {
public:
    Circle(double r) : m_radius(r) {}
    double area()      const override { return 3.14159 * m_radius * m_radius; }
    double perimeter() const override { return 2 * 3.14159 * m_radius; }
    void   draw()      const override { std::cout << "Drawing circle\n"; }
private:
    double m_radius;
};

class Rectangle : public Shape {
public:
    Rectangle(double w, double h) : m_w(w), m_h(h) {}
    double area()      const override { return m_w * m_h; }
    double perimeter() const override { return 2 * (m_w + m_h); }
    void   draw()      const override { std::cout << "Drawing rectangle\n"; }
private:
    double m_w, m_h;
};

// Usage
std::vector<std::unique_ptr<Shape>> shapes;
shapes.push_back(std::make_unique<Circle>(5.0));
shapes.push_back(std::make_unique<Rectangle>(4.0, 6.0));
for (const auto& s : shapes) {
    s->printInfo();
}
```

### Inheritance Modes

```cpp
class Base {
public:    int pub;
protected: int prot;
private:   int priv;
};

// public inheritance: pub→public, prot→protected, priv→inaccessible
class PublicDerived : public Base {};

// protected inheritance: pub→protected, prot→protected
class ProtectedDerived : protected Base {};

// private inheritance: pub→private, prot→private (implementation detail)
class PrivateDerived : private Base {};

// Multiple inheritance
class A { public: void hello() { std::cout << "A\n"; } };
class B { public: void world() { std::cout << "B\n"; } };
class C : public A, public B {};

C obj;
obj.hello();  // from A
obj.world();  // from B
```

### Virtual Table (vtable)

```cpp
// How virtual dispatch works:
// - Each class with virtual functions gets a vtable (array of function pointers)
// - Each object stores a hidden vptr pointing to its class's vtable
// - Virtual call: obj->vptr → vtable → function pointer → call

// sizeof(Base without virtual) = sizeof members only
// sizeof(Base with virtual)    = sizeof members + sizeof(vptr) (usually 8 bytes on 64-bit)

class NoVirtual { int x; };                  // sizeof = 4
class WithVirtual { virtual void f(); int x; }; // sizeof = 16 (4 + 4 pad + 8 vptr)
```

### `dynamic_cast` & RTTI

```cpp
Animal* a = new Dog("Rex", "Labrador");

// dynamic_cast — safe downcast (returns nullptr if wrong type)
Dog* d = dynamic_cast<Dog*>(a);
if (d != nullptr) {
    d->fetch();
}

// typeid — query runtime type
#include <typeinfo>
std::cout << typeid(*a).name();   // mangled name of Dog

// Note: requires RTTI. Disabled in embedded with -fno-rtti
// Prefer design patterns over dynamic_cast where possible
```

---

## 11. Templates

### Function Templates

```cpp
// Generic function — T deduced from argument
template<typename T>
T maximum(T a, T b) {
    return (a > b) ? a : b;
}

maximum(3, 5);         // T = int
maximum(3.0, 5.0);     // T = double
maximum('a', 'z');     // T = char

// Explicit specialisation
template<>
const char* maximum<const char*>(const char* a, const char* b) {
    return (std::strcmp(a, b) > 0) ? a : b;
}

// Multiple type parameters
template<typename T, typename U>
auto add(T a, U b) -> decltype(a + b) {
    return a + b;
}
add(1, 2.5);   // returns double
```

### Class Templates

```cpp
template<typename T>
class Stack {
public:
    void push(const T& item) {
        m_data.push_back(item);
    }
    void pop() {
        if (!m_data.empty()) m_data.pop_back();
    }
    T& top() { return m_data.back(); }
    bool empty() const { return m_data.empty(); }
    std::size_t size() const { return m_data.size(); }

private:
    std::vector<T> m_data;
};

Stack<int> intStack;
intStack.push(1);
intStack.push(2);
std::cout << intStack.top();   // 2

Stack<std::string> strStack;
strStack.push("hello");
```

### Non-Type Template Parameters

```cpp
// Size as template parameter — no heap needed
template<typename T, std::size_t N>
class FixedArray {
public:
    T& operator[](std::size_t i) { return m_data[i]; }
    std::size_t size() const { return N; }
private:
    T m_data[N];
};

FixedArray<int, 10> arr;   // 10 ints on stack
arr[0] = 42;
```

### Template Specialisation

```cpp
// Primary template
template<typename T>
struct IsPointer { static constexpr bool value = false; };

// Full specialisation for pointer types
template<typename T>
struct IsPointer<T*> { static constexpr bool value = true; };

static_assert(!IsPointer<int>::value);
static_assert( IsPointer<int*>::value);
```

### `constexpr if` (C++17) in Templates

```cpp
template<typename T>
std::string describe(T val) {
    if constexpr (std::is_integral_v<T>) {
        return "integer: " + std::to_string(val);
    } else if constexpr (std::is_floating_point_v<T>) {
        return "float: " + std::to_string(val);
    } else {
        return "other";
    }
}
```

---

## 12. The Standard Library (STL)

### Containers Overview

```
Container       | Header      | Access   | Insert   | Ordered | Key-Value
----------------|-------------|----------|----------|---------|----------
vector          | <vector>    | O(1)     | O(1) amort back | No  | No
array           | <array>     | O(1)     | N/A      | No      | No
deque           | <deque>     | O(1)     | O(1) front/back | No | No
list            | <list>      | O(n)     | O(1)     | No      | No
forward_list    | <forward_list>| O(n)  | O(1)     | No      | No
stack           | <stack>     | LIFO     | O(1)     | No      | No
queue           | <queue>     | FIFO     | O(1)     | No      | No
priority_queue  | <queue>     | max top  | O(log n) | Partial | No
set             | <set>       | O(log n) | O(log n) | Yes     | No
multiset        | <set>       | O(log n) | O(log n) | Yes     | No
map             | <map>       | O(log n) | O(log n) | Yes     | Yes
multimap        | <map>       | O(log n) | O(log n) | Yes     | Yes
unordered_set   | <unordered_set>| O(1) avg | O(1) avg | No  | No
unordered_map   | <unordered_map>| O(1) avg | O(1) avg | No  | Yes
```

### `std::vector` Deep Dive

```cpp
#include <vector>
std::vector<int> v = {3, 1, 4, 1, 5, 9, 2, 6};

// Modifiers
v.push_back(7);
v.emplace_back(8);        // construct in-place (avoids copy)
v.insert(v.begin() + 2, 99);
v.erase(v.begin());
v.clear();
v.resize(10, 0);          // resize to 10 elements, fill new with 0
v.assign(5, 1);           // replace with 5 ones

// Capacity
v.size();
v.capacity();
v.empty();
v.reserve(100);
v.shrink_to_fit();

// Iterators
v.begin(); v.end();       // forward iterators
v.rbegin(); v.rend();     // reverse iterators
v.cbegin(); v.cend();     // const iterators
```

### `std::map`

```cpp
#include <map>
std::map<std::string, int> scores;

// Insert
scores["Alice"] = 95;
scores["Bob"]   = 87;
scores.insert({"Charlie", 91});
scores.emplace("Dave", 88);

// Access
scores["Alice"];           // 95  (inserts if not exists — careful!)
scores.at("Alice");        // 95  (throws if not exists — safe)

// Find
auto it = scores.find("Bob");
if (it != scores.end()) {
    std::cout << it->first << ": " << it->second;   // "Bob: 87"
}

// Check existence (C++20)
scores.contains("Alice");   // true

// Iterate
for (const auto& [name, score] : scores) {  // structured bindings (C++17)
    std::cout << name << ": " << score << '\n';
}

// Erase
scores.erase("Bob");
```

### `std::unordered_map`

```cpp
#include <unordered_map>
// Same interface as map but O(1) average vs O(log n)
// NOT sorted — don't iterate expecting order
std::unordered_map<std::string, int> lookup;
lookup["key"] = 42;
```

### Algorithms

```cpp
#include <algorithm>
#include <numeric>

std::vector<int> v = {3, 1, 4, 1, 5, 9, 2, 6};

// Sorting
std::sort(v.begin(), v.end());                        // ascending
std::sort(v.begin(), v.end(), std::greater<int>());   // descending
std::sort(v.begin(), v.end(), [](int a, int b){ return a > b; }); // custom

// Searching
bool found = std::binary_search(v.begin(), v.end(), 5);
auto it = std::find(v.begin(), v.end(), 4);   // linear search
auto it2 = std::lower_bound(v.begin(), v.end(), 5); // first >= 5 (sorted)

// Min/Max
auto mn = std::min_element(v.begin(), v.end());
auto mx = std::max_element(v.begin(), v.end());
auto [lo, hi] = std::minmax_element(v.begin(), v.end()); // C++11

// Transformations
std::reverse(v.begin(), v.end());
std::rotate(v.begin(), v.begin() + 2, v.end());  // move first 2 to end
std::unique(v.begin(), v.end());   // remove consecutive duplicates

// Numeric
int sum = std::accumulate(v.begin(), v.end(), 0);
int product = std::accumulate(v.begin(), v.end(), 1, std::multiplies<int>());

// Count
int count = std::count(v.begin(), v.end(), 1);
int count_if = std::count_if(v.begin(), v.end(), [](int x){ return x > 3; });

// Filter + Transform (with output)
std::vector<int> evens;
std::copy_if(v.begin(), v.end(), std::back_inserter(evens),
             [](int x){ return x % 2 == 0; });

std::vector<int> squares(v.size());
std::transform(v.begin(), v.end(), squares.begin(),
               [](int x){ return x * x; });

// Fill
std::fill(v.begin(), v.end(), 0);
std::iota(v.begin(), v.end(), 1);   // 1, 2, 3, 4, ... (fill with increasing)
```

### Iterators

```cpp
// Iterator categories (from weakest to strongest):
// InputIterator       — read-once, forward only (e.g., istream)
// OutputIterator      — write-once, forward only (e.g., ostream)
// ForwardIterator     — read multiple times, forward (e.g., forward_list)
// BidirectionalIterator — forward + backward (e.g., list, map)
// RandomAccessIterator — O(1) jump anywhere (e.g., vector, array)

std::vector<int> v = {1, 2, 3, 4, 5};

// Manual iterator usage
auto it = v.begin();
++it;               // move to next: points to 2
*it = 99;           // modify: v is now {1, 99, 3, 4, 5}
it += 2;            // jump forward 2: points to 4 (random access)

// Reverse
for (auto rit = v.rbegin(); rit != v.rend(); ++rit) {
    std::cout << *rit << ' ';  // 5 4 3 99 1
}
```

---

## 13. Memory Management

### Stack vs Heap

```cpp
// STACK — automatic, fast, limited size (~1-8 MB)
void stackExample() {
    int x = 42;                  // on stack
    double arr[100];             // 800 bytes on stack
    std::string s = "hello";    // string object on stack (buffer may use heap)
}   // all destroyed automatically here

// HEAP — manual (or smart pointer), slower, large
void heapExample() {
    int* p = new int(42);               // allocate single int
    int* arr = new int[100];            // allocate array
    // ... use p and arr ...
    delete p;                           // free single
    delete[] arr;                       // free array — MUST use delete[]
}
// Forgetting delete = MEMORY LEAK
// Double delete = UNDEFINED BEHAVIOUR
// Accessing after delete = USE-AFTER-FREE
```

### `new` / `delete`

```cpp
// Basic allocation
int* p = new int;           // uninitialized
int* p2 = new int(42);      // initialized to 42
int* arr = new int[10]{};   // 10 zeros

// Deallocation
delete p;
delete p2;
delete[] arr;   // MUST match new[] with delete[]

// Placement new — construct at pre-allocated address
alignas(int) char buffer[sizeof(int)];
int* p3 = new (buffer) int(99);   // construct at buffer address
p3->~int();   // explicit destructor call when using placement new

// nothrow variant
int* p4 = new(std::nothrow) int[1000000];
if (p4 == nullptr) {
    // allocation failed
}
```

### RAII — Resource Acquisition Is Initialization

```cpp
// Core C++ idiom: acquire resource in constructor, release in destructor
// Guarantees cleanup even on exception or early return

class FileHandle {
public:
    explicit FileHandle(const char* path) {
        m_file = std::fopen(path, "r");
        if (!m_file) throw std::runtime_error("Cannot open file");
    }

    ~FileHandle() {
        if (m_file) std::fclose(m_file);  // always called
    }

    // Non-copyable: prevent double-close
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;

    // Movable
    FileHandle(FileHandle&& o) noexcept : m_file(o.m_file) { o.m_file = nullptr; }

    FILE* get() { return m_file; }

private:
    FILE* m_file;
};

void processFile(const char* path) {
    FileHandle f(path);      // file opened
    // ... process ...
    if (error) return;       // file closed here (destructor)
}   // file closed here (destructor)
```

### Smart Pointers — Full Detail

```cpp
#include <memory>

// ── unique_ptr ──────────────────────────────────────────────
auto u1 = std::make_unique<int>(42);  // preferred
int* u2 = new int(42);
auto u3 = std::unique_ptr<int>(u2);   // take ownership of raw ptr

*u1 = 100;
u1.get();          // raw pointer (don't delete it!)
u1.release();      // releases ownership, returns raw ptr (you must delete)
u1.reset();        // deletes and sets to nullptr
u1.reset(new int(5)); // deletes old, replaces with new

// Unique array
auto arr = std::make_unique<int[]>(10);
arr[0] = 42;

// Custom deleter
auto filePtr = std::unique_ptr<FILE, decltype(&std::fclose)>(
    std::fopen("test.txt", "r"), &std::fclose);

// ── shared_ptr ──────────────────────────────────────────────
auto sp1 = std::make_shared<std::string>("hello");
auto sp2 = sp1;            // both own the string
sp1.use_count();           // 2

sp1.reset();               // sp1 no longer owns it, use_count = 1
// string deleted when sp2 goes out of scope

// ── weak_ptr ────────────────────────────────────────────────
std::weak_ptr<int> wp;
{
    auto sp = std::make_shared<int>(42);
    wp = sp;
    auto locked = wp.lock();   // shared_ptr if still alive
    std::cout << *locked;      // 42
}   // sp destroyed, int deleted
auto locked2 = wp.lock();      // returns nullptr — object gone
```

---

## 14. Modern C++11/14/17 Features

### `auto` & Type Deduction

```cpp
auto i = 0;                    // int
auto d = 0.0;                  // double
auto s = std::string("hi");    // string
auto v = std::vector<int>{};   // vector<int>

// auto in function return (C++14)
auto multiply(int x, int y) { return x * y; }  // returns int

// Trailing return type (C++11)
auto divide(double x, double y) -> double { return x / y; }
```

### Uniform Initialization `{}`

```cpp
// Initialise anything with braces
int x{5};
double y{3.14};
std::vector<int> v{1, 2, 3};
std::map<std::string,int> m{{"a",1}, {"b",2}};

struct Point { int x, y; };
Point p{10, 20};

// Prevents narrowing conversions (catches bugs)
int i = 3.7;    // OK — silently truncates to 3
int j{3.7};     // ERROR — narrowing conversion (3.7 → 3 loses precision)
```

### Range-Based `for` (C++11)

```cpp
std::vector<int> v = {1, 2, 3};

for (int x : v) {}           // copy
for (int& x : v) {}          // reference (modify)
for (const int& x : v) {}    // const reference (read-only, no copy)
for (auto&& x : v) {}        // forwarding reference (best general form)
```

### `nullptr` (C++11)

```cpp
// Replaces NULL and 0 for pointers
int* p = nullptr;          // type-safe null pointer

void f(int*);
void f(int);
f(NULL);      // ambiguous: calls f(int) on most compilers
f(nullptr);   // unambiguous: calls f(int*)
```

### `enum class` (C++11)

```cpp
// Old enum — leaks into enclosing scope, implicit int conversion
enum Color { RED, GREEN, BLUE };
int x = RED;            // implicit conversion to int — dangerous

// enum class — scoped and strongly typed
enum class Direction { North, South, East, West };
Direction d = Direction::North;         // must use scope
// int y = Direction::North;           // ERROR — no implicit conversion
// Direction d2 = 0;                   // ERROR — cannot assign int

// Specify underlying type
enum class Status : uint8_t { OK=0, Error=1, Pending=2 };
```

### `constexpr` (C++11/14/17)

```cpp
// C++11: simple expression
constexpr int square(int x) { return x * x; }
constexpr int val = square(5);   // 25, computed at compile time

// C++14: can have local variables, loops
constexpr int factorial(int n) {
    int result = 1;
    for (int i = 2; i <= n; ++i) result *= i;
    return result;
}
static_assert(factorial(5) == 120);

// C++17: if constexpr in templates (see Templates section)
```

### Move Semantics (C++11)

```cpp
// Problem: copying large objects is expensive
std::vector<int> makeHuge() {
    std::vector<int> v(1000000);
    return v;          // Without move semantics: copy 1M ints
}                      // With move semantics (NRVO/RVO): zero copy

// std::move — cast to rvalue reference (enables move)
std::vector<int> a = {1, 2, 3};
std::vector<int> b = std::move(a);  // a is now empty — data transferred to b
// a is in "valid but unspecified state" — don't use without re-assigning

// Perfect forwarding
template<typename T>
void wrapper(T&& arg) {
    someFunction(std::forward<T>(arg));  // forwards lvalue as lvalue, rvalue as rvalue
}
```

### Structured Bindings (C++17)

```cpp
// Unpack tuples, pairs, structs, arrays
std::pair<int, std::string> p = {42, "hello"};
auto [num, str] = p;
std::cout << num << " " << str;   // 42 hello

std::map<std::string, int> m = {{"a", 1}, {"b", 2}};
for (const auto& [key, value] : m) {
    std::cout << key << "=" << value << '\n';
}

// With struct
struct Point { int x; int y; };
Point pt{3, 7};
auto [px, py] = pt;

// With array
int arr[3] = {1, 2, 3};
auto [a, b, c] = arr;
```

### `std::optional` (C++17)

```cpp
#include <optional>

// Return value that might not exist
std::optional<std::string> findUser(int id) {
    if (id == 1) return "Alice";
    if (id == 2) return "Bob";
    return std::nullopt;    // no value
}

auto user = findUser(1);
if (user.has_value()) {
    std::cout << user.value();       // "Alice"
    std::cout << *user;              // same
}
std::cout << user.value_or("Unknown"); // default if empty

// Without optional — you'd need bool + output param
// or special sentinel value (-1, "", etc.)
```

### `std::variant` (C++17)

```cpp
#include <variant>

// Type-safe union — holds exactly one of the listed types
std::variant<int, double, std::string> v;

v = 42;
v = 3.14;
v = std::string{"hello"};

// Access
std::get<std::string>(v);          // "hello" (throws if wrong type)
std::get_if<int>(&v);              // nullptr if not int

// Visit — pattern matching
std::visit([](auto&& val) {
    std::cout << val << '\n';
}, v);

// With typed visitor
struct Printer {
    void operator()(int i)                { std::cout << "int: " << i; }
    void operator()(double d)             { std::cout << "double: " << d; }
    void operator()(const std::string& s) { std::cout << "string: " << s; }
};
std::visit(Printer{}, v);
```

### `std::string_view` (C++17)

```cpp
#include <string_view>

// Non-owning view into a string — no copy, no allocation
void print(std::string_view sv) {
    std::cout << sv;   // works with const char*, std::string, std::string_view
}

print("hello literal");           // no copy
print(std::string{"hello str"});  // no copy (view into string's buffer)

// Useful for lightweight string passing
std::string_view sv = "hello world";
sv.substr(6, 5);    // "world" — returns string_view (no allocation!)
sv.find("world");   // 6
```

### `if constexpr` (C++17)

```cpp
// Compile-time branching — eliminates dead branches entirely
template<typename T>
void serialize(T value) {
    if constexpr (std::is_integral_v<T>) {
        writeInt(static_cast<int64_t>(value));
    } else if constexpr (std::is_floating_point_v<T>) {
        writeDouble(static_cast<double>(value));
    } else {
        writeString(std::to_string(value));
    }
}
// Only the matching branch is compiled.
// Unlike regular if — other branches don't need to compile.
```

### Fold Expressions (C++17)

```cpp
// Apply operator across all arguments of a variadic template
template<typename... Args>
auto sumAll(Args... args) {
    return (args + ...);    // unary right fold: arg1 + (arg2 + (arg3 + ...))
}

template<typename... Args>
void printAll(Args&&... args) {
    ((std::cout << args << ' '), ...);  // fold with comma operator
}

sumAll(1, 2, 3, 4);     // 10
printAll(1, "hello", 3.14);
```

---

## 15. File I/O

```cpp
#include <fstream>
#include <sstream>

// ── Write to file ──────────────────────────────────────────
{
    std::ofstream file("output.txt");
    if (file.is_open()) {
        file << "Line 1\n";
        file << "Value: " << 42 << '\n';
    }
}   // file closed automatically (RAII)

// ── Read from file ─────────────────────────────────────────
{
    std::ifstream file("input.txt");
    if (!file) {
        std::cerr << "Failed to open\n";
        return;
    }

    // Read line by line
    std::string line;
    while (std::getline(file, line)) {
        std::cout << line << '\n';
    }

    // Read word by word
    std::string word;
    while (file >> word) {
        std::cout << word << ' ';
    }

    // Read entire file into string
    std::ostringstream ss;
    ss << file.rdbuf();
    std::string content = ss.str();
}

// ── Binary I/O ─────────────────────────────────────────────
struct Packet { uint32_t id; uint8_t data[8]; };
Packet pkt{0x100, {1,2,3,4,5,6,7,8}};

std::ofstream binFile("data.bin", std::ios::binary);
binFile.write(reinterpret_cast<const char*>(&pkt), sizeof(pkt));

std::ifstream binIn("data.bin", std::ios::binary);
Packet readPkt;
binIn.read(reinterpret_cast<char*>(&readPkt), sizeof(readPkt));

// ── String streams ─────────────────────────────────────────
std::ostringstream oss;
oss << "Speed: " << 120.5 << " km/h";
std::string log = oss.str();

std::istringstream iss("10 20 30");
int a, b, c;
iss >> a >> b >> c;   // a=10, b=20, c=30
```

---

## 16. Exception Handling

```cpp
#include <stdexcept>

// throw
void divide(int a, int b) {
    if (b == 0) throw std::invalid_argument("Division by zero");
    return a / b;
}

// try / catch
try {
    int result = divide(10, 0);
} catch (const std::invalid_argument& e) {
    std::cerr << "Invalid arg: " << e.what() << '\n';
} catch (const std::exception& e) {
    std::cerr << "Exception: " << e.what() << '\n';
} catch (...) {
    std::cerr << "Unknown exception\n";
}

// Standard exception hierarchy
// std::exception
//   ├── std::logic_error
//   │     ├── std::invalid_argument
//   │     ├── std::out_of_range
//   │     └── std::length_error
//   └── std::runtime_error
//         ├── std::overflow_error
//         ├── std::underflow_error
//         └── std::range_error

// Custom exception
class SensorException : public std::runtime_error {
public:
    explicit SensorException(const std::string& msg, int sensorId)
        : std::runtime_error(msg), m_sensorId(sensorId) {}
    int sensorId() const { return m_sensorId; }
private:
    int m_sensorId;
};

// noexcept — declares function won't throw (enables optimisations)
int safeAdd(int a, int b) noexcept {
    return a + b;
}

// RAII + exceptions: destructors always called, resources always freed
// NOTE: In embedded/MISRA — exceptions are disabled. Use return codes instead.
```

---

## 17. Namespaces

```cpp
// Define namespace
namespace Math {
    const double PI = 3.14159265358979;
    double sin(double x);
    double cos(double x);

    namespace Advanced {   // nested namespace
        double integrate(double(*f)(double), double a, double b);
    }
}

// Access
double result = Math::sin(Math::PI / 2.0);
double i = Math::Advanced::integrate(Math::sin, 0, Math::PI);

// using declaration — bring one name in
using Math::PI;
std::cout << PI;

// using directive — bring entire namespace in (avoid in headers)
using namespace Math;
std::cout << sin(PI);

// Inline namespace (C++11) — for versioning
namespace Lib {
    inline namespace v2 {  // inline: Lib::v2::func accessible as Lib::func
        void func();
    }
    namespace v1 {
        void func();
    }
}
Lib::func();    // calls v2::func() (the inline one)

// Anonymous namespace — replaces static at file scope
namespace {
    void helperFunction() {}  // visible only in this translation unit
    int moduleState = 0;
}
```

---

## 18. Preprocessor

```cpp
// ── Include guards ─────────────────────────────────────────
#ifndef MY_HEADER_H
#define MY_HEADER_H
// ... header content ...
#endif

// Or (non-standard but universal):
#pragma once

// ── Macros ────────────────────────────────────────────────
#define STRINGIFY(x) #x           // stringification
#define CONCAT(a,b) a##b          // token pasting
#define MAX(a,b) ((a)>(b)?(a):(b)) // function-like (fragile — prefer inline)

// ── Conditional compilation ────────────────────────────────
#define DEBUG_MODE 1

#ifdef DEBUG_MODE
    #define LOG(x) std::cout << x << '\n'
#else
    #define LOG(x)
#endif

// ── Predefined macros ──────────────────────────────────────
std::cout << __FILE__;       // "main.cpp"
std::cout << __LINE__;       // current line number (int)
std::cout << __func__;       // current function name
std::cout << __DATE__;       // "Jan  1 2025"
std::cout << __TIME__;       // "12:34:56"
std::cout << __cplusplus;    // 201703L for C++17

// ── Diagnostic ────────────────────────────────────────────
#warning "This feature is deprecated"    // compiler warning
#error "Platform not supported"          // compile error

// ── static_assert (C++11) — prefer over #error ────────────
static_assert(sizeof(int) == 4, "int must be 4 bytes");
static_assert(sizeof(float) == 4, "float must be IEEE 754 single");
```

---

## 19. Concurrency (`std::thread`)

```cpp
#include <thread>
#include <mutex>
#include <condition_variable>
#include <atomic>
#include <future>

// ── Basic thread ──────────────────────────────────────────
void worker(int id) {
    std::cout << "Worker " << id << " started\n";
}

std::thread t1(worker, 1);
std::thread t2([](){ std::cout << "Lambda thread\n"; });

t1.join();   // wait for t1 to finish
t2.join();
// t.detach(); // let thread run independently (be careful)

// ── Mutex & lock_guard ────────────────────────────────────
std::mutex mtx;
int sharedCounter = 0;

void increment() {
    std::lock_guard<std::mutex> lock(mtx);  // RAII — unlocked at scope exit
    ++sharedCounter;
}

// unique_lock — more flexible (can unlock/relock)
void trySomething() {
    std::unique_lock<std::mutex> lock(mtx);
    // do something under lock
    lock.unlock();
    // do something outside lock
    lock.lock();
    // back under lock
}

// ── atomic ────────────────────────────────────────────────
std::atomic<int> atomicCounter{0};
void atomicIncrement() {
    ++atomicCounter;   // atomic — no mutex needed for simple ops
}

// ── condition_variable ────────────────────────────────────
std::mutex cvMtx;
std::condition_variable cv;
bool dataReady = false;

// Producer
void produce() {
    {
        std::lock_guard<std::mutex> lock(cvMtx);
        dataReady = true;
    }
    cv.notify_one();
}

// Consumer
void consume() {
    std::unique_lock<std::mutex> lock(cvMtx);
    cv.wait(lock, []{ return dataReady; });  // spurious wakeup safe
    // process data
}

// ── std::future / std::async ──────────────────────────────
std::future<int> result = std::async(std::launch::async, []() {
    return expensiveComputation();
});

// Do other work here...
int value = result.get();   // block until result ready

// std::promise — manually set future result
std::promise<int> prom;
std::future<int> fut = prom.get_future();

std::thread([&prom](){
    prom.set_value(42);
}).detach();

int val = fut.get();   // 42
```

---

## 20. Best Practices & Common Pitfalls

### The Big Four Anti-Patterns

```cpp
// ❌ 1. Memory leak — forgetting delete
void leak() {
    int* p = new int[1000];
    if (someCondition()) return;   // leak! never reaches delete
    delete[] p;
}
// ✅ Fix: use unique_ptr or vector

// ❌ 2. Use-after-free
int* p = new int(5);
delete p;
*p = 10;    // UNDEFINED BEHAVIOUR — p points to freed memory
// ✅ Fix: p = nullptr after delete; or use smart pointers

// ❌ 3. Buffer overflow
char buf[10];
strcpy(buf, "This is too long for the buffer");  // overwrites stack!
// ✅ Fix: use std::string or strncpy with size check

// ❌ 4. Uninitialized variable
int x;
if (x > 0) {}   // x has garbage value
// ✅ Fix: always initialise: int x = 0;
```

### Undefined Behaviour (UB) — The Most Dangerous

```cpp
// Must be avoided at ALL costs — compiler may produce any output

// Signed integer overflow
int x = INT_MAX;
int y = x + 1;    // UB! (wrap defined for unsigned, not signed)

// Null pointer dereference
int* p = nullptr;
*p = 5;           // UB (likely crash, but not guaranteed)

// Out-of-bounds access
int arr[5];
arr[10] = 1;      // UB — stack corruption

// Strict aliasing violation
float f = 1.0f;
int* ip = reinterpret_cast<int*>(&f);   // UB (type aliasing)
// Exception: char* and void* can alias anything

// Use std::memcpy for type punning instead:
int bits;
std::memcpy(&bits, &f, sizeof(bits));  // well-defined
```

### Const Correctness

```cpp
// Mark everything that shouldn't change as const
const int MAX_SPEED = 200;              // constant value
void read(const std::vector<int>& v);   // const reference: no copy, no modification
int getValue() const;                   // const method: doesn't modify object
const int* ptr;                         // ptr to const data
```

### Naming Conventions

```
Variable:     camelCase or snake_case  (speed, vehicleSpeed, vehicle_speed)
Function:     camelCase                (computeSpeed, getStatus)
Class:        PascalCase               (CarEngine, SensorData)
Constant:     UPPER_SNAKE or kCamel   (MAX_SPEED, kMaxSpeed)
Member var:   m_ prefix               (m_speed, m_engineState)
Global:       g_ prefix               (g_systemState)
Static:       s_ prefix               (s_instanceCount)
Template:     T, U, V or descriptive  (template<typename T>)
```

### `const` vs `constexpr` vs `#define`

```cpp
#define PI 3.14f          // No type, no scope, no debugger, text substitution
const float PI = 3.14f;   // Typed, scoped, runtime constant (may use RAM)
constexpr float PI = 3.14f; // Typed, scoped, compile-time constant (no RAM)

// Use constexpr whenever possible for constants
```

### Rule of Zero / Three / Five

```cpp
// Rule of Zero: if your members manage themselves (vector, string, unique_ptr)
// → don't write any of: destructor, copy ctor, copy assign, move ctor, move assign
// → let the compiler generate all five for you

// Rule of Three (pre-C++11):
// If you define any of: destructor, copy ctor, copy assign
// → define all three

// Rule of Five (C++11+):
// If you define any of the five special functions
// → define all five (or explicitly = delete or = default them)

class Complete {
public:
    Complete() = default;
    ~Complete() = default;
    Complete(const Complete&) = default;
    Complete& operator=(const Complete&) = default;
    Complete(Complete&&) = default;
    Complete& operator=(Complete&&) = default;
};
```

### Header File Best Practices

```cpp
// my_class.h
#pragma once                         // include guard
#include <cstdint>                   // only necessary includes
// NEVER: using namespace std;       // pollutes every including file

class MyClass {
public:
    explicit MyClass(int value);     // explicit: no implicit conversion
    int getValue() const;
    void setValue(int value);

private:
    int m_value;                     // private members
};

// my_class.cpp
#include "my_class.h"
using namespace std;  // OK in .cpp files only

MyClass::MyClass(int value) : m_value(value) {}
int MyClass::getValue() const { return m_value; }
void MyClass::setValue(int value) { m_value = value; }
```

### Performance Tips

```cpp
// 1. Use emplace_back instead of push_back
v.push_back(MyClass(1, 2));   // construct then copy/move
v.emplace_back(1, 2);         // construct in-place (faster)

// 2. Reserve vector capacity upfront
std::vector<int> v;
v.reserve(1000);               // avoids reallocations

// 3. Pass large objects by const reference, not by value
void process(const BigStruct& s);   // no copy
void process(BigStruct s);          // copy every call

// 4. Prefer prefix increment for iterators
++it;   // no temporary created
it++;   // creates temporary (wasteful for complex iterators)

// 5. Move instead of copy for temporaries
std::string a = "hello";
std::string b = std::move(a);  // a is now empty, no string allocation

// 6. Use string_view for read-only string parameters
void log(std::string_view msg);  // works with any string type, no copy
```

---

## Quick Reference: C++ Standard Library Headers

```
Header           | Contents
-----------------|--------------------------------------------------
<iostream>       | cin, cout, cerr, endl
<string>         | std::string
<string_view>    | std::string_view (C++17)
<vector>         | std::vector
<array>          | std::array
<map>            | std::map, std::multimap
<unordered_map>  | std::unordered_map
<set>            | std::set, std::multiset
<unordered_set>  | std::unordered_set
<queue>          | std::queue, std::priority_queue
<stack>          | std::stack
<list>           | std::list, std::forward_list
<algorithm>      | sort, find, transform, copy_if, ...
<numeric>        | accumulate, iota, inner_product
<functional>     | std::function, std::bind, std::less, ...
<memory>         | unique_ptr, shared_ptr, weak_ptr, make_unique
<optional>       | std::optional (C++17)
<variant>        | std::variant (C++17)
<tuple>          | std::tuple, std::make_tuple, std::get
<chrono>         | time_point, duration, system_clock
<thread>         | std::thread
<mutex>          | std::mutex, std::lock_guard, std::unique_lock
<atomic>         | std::atomic
<condition_variable> | std::condition_variable
<future>         | std::future, std::promise, std::async
<fstream>        | std::ifstream, std::ofstream
<sstream>        | std::istringstream, std::ostringstream
<cstdint>        | uint8_t, int32_t, fixed-width types
<cmath>          | sin, cos, sqrt, abs, pow, floor, ceil
<cstring>        | strlen, strcpy, memcpy, memset
<cassert>        | assert()
<stdexcept>      | runtime_error, invalid_argument, out_of_range
<typeinfo>       | typeid, type_info
<limits>         | std::numeric_limits<T>::max(), min(), ...
<type_traits>    | is_integral, is_same, enable_if, ... (C++11)
```

---

*File: CPP_General_Learning_Guide.md | cpp_automotive study series*
*Standards: C++11, C++14, C++17 | Compiler: GCC 12+ / Clang 14+*
