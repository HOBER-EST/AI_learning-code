export interface Example {
  id: string;
  title: string;
  code: string;
}

export const EXAMPLES: Example[] = [
  {
    id: "fact",
    title: "阶乘（线性递归）",
    code: `def fact(n):
    """
    >>> fact(4)
    24
    """
    if n == 0:
        return 1
    return n * fact(n - 1)

result = fact(4)
`,
  },
  {
    id: "fib",
    title: "斐波那契（树递归）",
    code: `def fib(n):
    """
    >>> fib(5)
    5
    """
    if n <= 1:
        return n
    return fib(n - 1) + fib(n - 2)

result = fib(5)
`,
  },
  {
    id: "cascade",
    title: "cascade（递归中的 print 顺序）",
    code: `def cascade(n):
    if n < 10:
        print(n)
    else:
        print(n)
        cascade(n // 10)
        print(n)

cascade(123)
`,
  },
  {
    id: "hanoi",
    title: "汉诺塔",
    code: `def move_stack(n, start, end):
    """把 n 个盘子从 start 柱移动到 end 柱。"""
    if n == 1:
        print("把盘子从", start, "移到", end)
    else:
        other = 6 - start - end
        move_stack(n - 1, start, other)
        move_stack(1, start, end)
        move_stack(n - 1, other, end)

move_stack(3, 1, 3)
`,
  },
  {
    id: "closure",
    title: "高阶函数与 parent 帧",
    code: `def make_adder(n):
    def adder(k):
        return n + k
    return adder

add_three = make_adder(3)
x = add_three(4)
square = lambda y: y * y
z = square(x)
`,
  },
  {
    id: "link",
    title: "Link 链表：构建与修改",
    code: `def link_map(f, s):
    """返回把 f 作用到每个元素后的新链表。"""
    if s is Link.empty:
        return s
    return Link(f(s.first), link_map(f, s.rest))

s = Link(1, Link(2, Link(3)))
t = link_map(lambda x: x * 10, s)
s.rest.first = 99   # 修改：t 不受影响
print(s, t)
`,
  },
  {
    id: "tree",
    title: "Tree：求和与修改",
    code: `def total(t):
    return t.label + sum([total(b) for b in t.branches])

def double(t):
    t.label = t.label * 2
    for b in t.branches:
        double(b)

t = Tree(1, [Tree(2, [Tree(4)]), Tree(3)])
s = total(t)
double(t)
`,
  },
  {
    id: "adt",
    title: "函数式 tree ADT",
    code: `def leaves(t):
    """返回所有叶子的 label 列表。

    >>> leaves(tree(1, [tree(2), tree(3, [tree(4)])]))
    [2, 4]
    """
    if is_leaf(t):
        return [label(t)]
    return sum([leaves(b) for b in branches(t)], [])

t = tree(1, [tree(2), tree(3, [tree(4)])])
result = leaves(t)
`,
  },
  {
    id: "aliasing",
    title: "列表与别名",
    code: `a = [1, 2, 3]
b = a
c = list(a)
b.append(4)
nested = [a, [5, 6]]
`,
  },
  {
    id: "bug",
    title: "有 bug 的递归（试试 AI 导师）",
    code: `def sum_digits(n):
    """
    >>> sum_digits(2013)
    6
    >>> sum_digits(7)
    7
    """
    last = n % 10
    sum_digits(n // 10)
`,
  },
];
