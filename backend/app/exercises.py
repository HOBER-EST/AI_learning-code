"""Interactive CS61A-style exercises on Recursion, Linked Lists (Link) and Trees.

Each exercise ships with:

* ``starter`` - the code shown in the editor (docstring doctests are the
  *visible* tests);
* ``hidden_tests`` - extra doctest-format cases only run on submission;
* ``solution`` - a reference solution (revealed on request, and used by the
  test-suite to check that every exercise is solvable);
* ``hints`` - progressive hints, from gentle to specific;
* ``trace`` - a call appended to the code when visualizing it;
* ``constraints`` - structural requirements checked with the AST
  (e.g. "must be recursive", "no loops").
"""

from __future__ import annotations

import ast
import doctest
import textwrap
from dataclasses import dataclass, field

TOPICS = {
    "recursion": {
        "title": "递归 Recursion",
        "description": "把问题拆成更小的同类问题：先写基本情况（base case），再相信递归调用（recursive leap of faith）。",
    },
    "link": {
        "title": "链表 Linked List",
        "description": "Link 由 first 与 rest 组成，rest 要么是另一个 Link，要么是 Link.empty。",
    },
    "tree": {
        "title": "树 Tree",
        "description": "树由 label 和 branches 组成；大多数树问题的递归都是：处理当前节点 + 对每个分支递归。",
    },
}


@dataclass
class Exercise:
    id: str
    topic: str
    title: str
    difficulty: int  # 1 = easy, 2 = medium, 3 = hard
    function: str
    description: str
    starter: str
    solution: str
    hidden_tests: str
    hints: list[str]
    trace: str
    concepts: list[str] = field(default_factory=list)
    constraints: list[dict] = field(default_factory=list)

    @property
    def visible_tests(self) -> str:
        docstrings = [
            ast.get_docstring(node) or ""
            for node in ast.parse(self.starter).body
            if isinstance(node, ast.FunctionDef)
        ]
        parser = doctest.DocTestParser()
        return "".join(_examples_to_text(parser.get_examples(d)) for d in docstrings)

    @property
    def all_tests(self) -> str:
        return self.visible_tests + textwrap.dedent(self.hidden_tests).strip("\n") + "\n"

    def summary(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "title": self.title,
            "difficulty": self.difficulty,
            "function": self.function,
            "concepts": self.concepts,
        }

    def detail(self) -> dict:
        return {
            **self.summary(),
            "description": self.description,
            "starter": self.starter,
            "hints": self.hints,
            "trace": self.trace,
            "constraints": self.constraints,
            "hidden_test_count": len(doctest.DocTestParser().get_examples(self.hidden_tests)),
        }


def _examples_to_text(examples) -> str:
    out = []
    for ex in examples:
        lines = ex.source.rstrip("\n").split("\n")
        out.append(">>> " + lines[0])
        out.extend("... " + line for line in lines[1:])
        if ex.want:
            out.append(ex.want.rstrip("\n"))
    return "\n".join(out) + "\n" if out else ""


def _code(text: str) -> str:
    return textwrap.dedent(text).strip("\n") + "\n"


RECURSIVE = {"type": "recursive"}
NO_LOOPS = {"type": "no_loops"}

EXERCISES: list[Exercise] = [
    # ------------------------------------------------------------ recursion
    Exercise(
        id="factorial",
        topic="recursion",
        title="阶乘 factorial",
        difficulty=1,
        function="factorial",
        concepts=["基本情况", "线性递归"],
        constraints=[RECURSIVE],
        description=_code(
            """
            实现 `factorial(n)`，返回 `n!`。规定 `0! = 1`。

            **要求：** 必须使用递归，不能使用循环。

            思考：`factorial(n)` 和 `factorial(n - 1)` 之间是什么关系？最小、可以直接回答的问题是什么？
            """
        ),
        starter=_code(
            '''
            def factorial(n):
                """返回 n 的阶乘。

                >>> factorial(0)
                1
                >>> factorial(4)
                24
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def factorial(n):
                """返回 n 的阶乘。

                >>> factorial(0)
                1
                >>> factorial(4)
                24
                """
                if n == 0:
                    return 1
                return n * factorial(n - 1)
            '''
        ),
        hidden_tests="""
            >>> factorial(1)
            1
            >>> factorial(6)
            720
            >>> factorial(12)
            479001600
        """,
        hints=[
            "基本情况：当 n == 0 时，答案可以直接写出来。",
            "递归情况：n! = n × (n-1)!，而 (n-1)! 正好就是 factorial(n - 1)。",
            "别忘了 return 递归调用的结果。",
        ],
        trace="result = factorial(4)",
    ),
    Exercise(
        id="sum_digits",
        topic="recursion",
        title="数位之和 sum_digits",
        difficulty=1,
        function="sum_digits",
        concepts=["数位拆分", "// 与 %"],
        constraints=[RECURSIVE, NO_LOOPS],
        description=_code(
            """
            实现 `sum_digits(n)`，返回非负整数 `n` 各位数字之和。

            提示：`n % 10` 取出最后一位，`n // 10` 去掉最后一位。

            **要求：** 使用递归，不能使用 `for` / `while`。
            """
        ),
        starter=_code(
            '''
            def sum_digits(n):
                """返回 n 的各位数字之和。

                >>> sum_digits(7)
                7
                >>> sum_digits(2013)
                6
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def sum_digits(n):
                """返回 n 的各位数字之和。

                >>> sum_digits(7)
                7
                >>> sum_digits(2013)
                6
                """
                if n < 10:
                    return n
                return n % 10 + sum_digits(n // 10)
            '''
        ),
        hidden_tests="""
            >>> sum_digits(10)
            1
            >>> sum_digits(4224)
            12
            >>> sum_digits(1234567890)
            45
        """,
        hints=[
            "一位数的数位之和就是它自己——这就是基本情况。",
            "sum_digits(2013) = 3 + sum_digits(201)。",
        ],
        trace="total = sum_digits(2013)",
    ),
    Exercise(
        id="num_eights",
        topic="recursion",
        title="数 8 的个数 num_eights",
        difficulty=1,
        function="num_eights",
        concepts=["数位拆分", "条件累加"],
        constraints=[RECURSIVE, NO_LOOPS],
        description=_code(
            """
            实现 `num_eights(n)`：返回正整数 `n` 的各个数位中数字 8 出现的次数。

            （CS61A HW 经典题）**要求：** 使用递归，不能使用循环。
            """
        ),
        starter=_code(
            '''
            def num_eights(n):
                """返回 n 中数字 8 出现的次数。

                >>> num_eights(3)
                0
                >>> num_eights(8)
                1
                >>> num_eights(88888888)
                8
                >>> num_eights(2638)
                1
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def num_eights(n):
                """返回 n 中数字 8 出现的次数。

                >>> num_eights(3)
                0
                >>> num_eights(8)
                1
                >>> num_eights(88888888)
                8
                >>> num_eights(2638)
                1
                """
                if n == 0:
                    return 0
                if n % 10 == 8:
                    return 1 + num_eights(n // 10)
                return num_eights(n // 10)
            '''
        ),
        hidden_tests="""
            >>> num_eights(86380)
            2
            >>> num_eights(12345)
            0
            >>> num_eights(808)
            2
        """,
        hints=[
            "只看最后一位：它是不是 8？剩下的位交给 num_eights(n // 10)。",
            "当 n 变成 0 时，没有数位了，8 的个数是 0。",
        ],
        trace="count = num_eights(8638)",
    ),
    Exercise(
        id="hailstone",
        topic="recursion",
        title="冰雹序列 hailstone",
        difficulty=1,
        function="hailstone",
        concepts=["print 与 return 的区别"],
        constraints=[RECURSIVE],
        description=_code(
            """
            冰雹序列：从 `n` 开始，若 `n` 为偶数则除以 2，否则变成 `3n + 1`，直到 `n == 1`。

            实现 `hailstone(n)`：**打印**序列中的每个数（每行一个），并**返回**序列的长度。

            注意区分 `print`（显示在屏幕上）与 `return`（交给调用者）。
            """
        ),
        starter=_code(
            '''
            def hailstone(n):
                """打印从 n 开始的冰雹序列，返回其长度。

                >>> a = hailstone(10)
                10
                5
                16
                8
                4
                2
                1
                >>> a
                7
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def hailstone(n):
                """打印从 n 开始的冰雹序列，返回其长度。

                >>> a = hailstone(10)
                10
                5
                16
                8
                4
                2
                1
                >>> a
                7
                """
                print(n)
                if n == 1:
                    return 1
                elif n % 2 == 0:
                    return 1 + hailstone(n // 2)
                else:
                    return 1 + hailstone(3 * n + 1)
            '''
        ),
        hidden_tests="""
            >>> b = hailstone(1)
            1
            >>> b
            1
            >>> c = hailstone(6)
            6
            3
            10
            5
            16
            8
            4
            2
            1
            >>> c
            9
        """,
        hints=[
            "每次调用先 print(n)。",
            "长度 = 1（当前这个数）+ 剩余序列的长度。",
        ],
        trace="length = hailstone(6)",
    ),
    Exercise(
        id="count_stair_ways",
        topic="recursion",
        title="爬楼梯 count_stair_ways",
        difficulty=2,
        function="count_stair_ways",
        concepts=["树递归", "重复计算"],
        constraints=[RECURSIVE],
        description=_code(
            """
            你要爬 `n` 级台阶，每次可以走 1 级或 2 级。共有多少种不同的走法？

            这是一个**树递归**问题：每一步都有两种选择。可视化时观察递归调用树——你会发现大量重复的子问题（这正是记忆化 memoization 的动机）。
            """
        ),
        starter=_code(
            '''
            def count_stair_ways(n):
                """返回爬 n 级台阶（每次 1 或 2 级）的走法数。

                >>> count_stair_ways(1)
                1
                >>> count_stair_ways(2)
                2
                >>> count_stair_ways(4)
                5
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def count_stair_ways(n):
                """返回爬 n 级台阶（每次 1 或 2 级）的走法数。

                >>> count_stair_ways(1)
                1
                >>> count_stair_ways(2)
                2
                >>> count_stair_ways(4)
                5
                """
                if n == 0:
                    return 1
                if n < 0:
                    return 0
                return count_stair_ways(n - 1) + count_stair_ways(n - 2)
            '''
        ),
        hidden_tests="""
            >>> count_stair_ways(3)
            3
            >>> count_stair_ways(10)
            89
        """,
        hints=[
            "第一步要么走 1 级，要么走 2 级——两种情况的走法数相加。",
            "正好走到顶（n == 0）算 1 种走法；走过头（n < 0）算 0 种。",
        ],
        trace="ways = count_stair_ways(4)",
    ),
    Exercise(
        id="pascal",
        topic="recursion",
        title="帕斯卡三角 pascal",
        difficulty=2,
        function="pascal",
        concepts=["树递归", "多个基本情况"],
        constraints=[RECURSIVE],
        description=_code(
            """
            帕斯卡三角中，每个数等于它左上方与正上方两个数之和：

            ```
            1
            1 1
            1 2 1
            1 3 3 1
            1 4 6 4 1
            ```

            实现 `pascal(row, column)`，返回第 `row` 行第 `column` 列（都从 0 开始）的值；若位置在三角形之外，返回 0。
            """
        ),
        starter=_code(
            '''
            def pascal(row, column):
                """返回帕斯卡三角中 (row, column) 位置的值。

                >>> pascal(0, 0)
                1
                >>> pascal(0, 5)
                0
                >>> pascal(3, 2)
                3
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def pascal(row, column):
                """返回帕斯卡三角中 (row, column) 位置的值。

                >>> pascal(0, 0)
                1
                >>> pascal(0, 5)
                0
                >>> pascal(3, 2)
                3
                """
                if column == 0:
                    return 1
                if row == 0:
                    return 0
                return pascal(row - 1, column) + pascal(row - 1, column - 1)
            '''
        ),
        hidden_tests="""
            >>> pascal(4, 2)
            6
            >>> pascal(6, 3)
            20
            >>> pascal(2, 3)
            0
        """,
        hints=[
            "第 0 列永远是 1；第 0 行除了第 0 列之外都是 0。",
            "pascal(row, column) = pascal(row - 1, column) + pascal(row - 1, column - 1)",
        ],
        trace="value = pascal(3, 2)",
    ),
    Exercise(
        id="count_partitions",
        topic="recursion",
        title="整数划分 count_partitions",
        difficulty=2,
        function="count_partitions",
        concepts=["树递归", "用 / 不用最大部件"],
        constraints=[RECURSIVE],
        description=_code(
            """
            把正整数 `n` 写成若干个**不超过 `m`** 的正整数之和（不计顺序），共有多少种写法？

            例如 `count_partitions(6, 4) == 9`：
            `2+4, 1+1+4, 3+3, 1+2+3, 1+1+1+3, 2+2+2, 1+1+2+2, 1+1+1+1+2, 1+1+1+1+1+1`。

            经典思路：要么**使用**至少一个 `m`，要么**完全不用** `m`。
            """
        ),
        starter=_code(
            '''
            def count_partitions(n, m):
                """返回用不超过 m 的正整数划分 n 的方法数。

                >>> count_partitions(6, 4)
                9
                >>> count_partitions(5, 5)
                7
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def count_partitions(n, m):
                """返回用不超过 m 的正整数划分 n 的方法数。

                >>> count_partitions(6, 4)
                9
                >>> count_partitions(5, 5)
                7
                """
                if n == 0:
                    return 1
                elif n < 0:
                    return 0
                elif m == 0:
                    return 0
                with_m = count_partitions(n - m, m)
                without_m = count_partitions(n, m - 1)
                return with_m + without_m
            '''
        ),
        hidden_tests="""
            >>> count_partitions(10, 10)
            42
            >>> count_partitions(15, 15)
            176
            >>> count_partitions(20, 20)
            627
        """,
        hints=[
            "两种情况：使用 m（问题变成 count_partitions(n - m, m)），不使用 m（变成 count_partitions(n, m - 1)）。",
            "基本情况有三个：n == 0（找到一种划分），n < 0（失败），m == 0（没有可用的数了）。",
        ],
        trace="ways = count_partitions(5, 3)",
    ),
    Exercise(
        id="paths",
        topic="recursion",
        title="网格路径 paths",
        difficulty=2,
        function="paths",
        concepts=["树递归", "网格"],
        constraints=[RECURSIVE],
        description=_code(
            """
            一只虫子在 `m × n` 的网格左下角，只能**向上**或**向右**移动，要到达右上角。共有多少条不同路径？
            """
        ),
        starter=_code(
            '''
            def paths(m, n):
                """返回 m 行 n 列网格中从左下角到右上角的路径数。

                >>> paths(2, 2)
                2
                >>> paths(5, 7)
                210
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def paths(m, n):
                """返回 m 行 n 列网格中从左下角到右上角的路径数。

                >>> paths(2, 2)
                2
                >>> paths(5, 7)
                210
                """
                if m == 1 or n == 1:
                    return 1
                return paths(m - 1, n) + paths(m, n - 1)
            '''
        ),
        hidden_tests="""
            >>> paths(117, 1)
            1
            >>> paths(1, 157)
            1
            >>> paths(3, 3)
            6
        """,
        hints=[
            "只有一行或一列时，只有一条路。",
            "第一步向上走或向右走，两种情况的路径数相加。",
        ],
        trace="n_paths = paths(3, 3)",
    ),
    # ------------------------------------------------------------ linked lists
    Exercise(
        id="link_to_list",
        topic="link",
        title="链表转列表 link_to_list",
        difficulty=1,
        function="link_to_list",
        concepts=["Link.empty", "first / rest"],
        constraints=[RECURSIVE],
        description=_code(
            """
            实现 `link_to_list(link)`，返回一个 Python 列表，包含链表中的所有元素（按顺序）。

            链表的结构：`link.first` 是第一个元素，`link.rest` 是剩下的链表；空链表是 `Link.empty`。
            """
        ),
        starter=_code(
            '''
            def link_to_list(link):
                """把链表转换成 Python 列表。

                >>> link = Link(1, Link(2, Link(3, Link(4))))
                >>> link_to_list(link)
                [1, 2, 3, 4]
                >>> link_to_list(Link.empty)
                []
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def link_to_list(link):
                """把链表转换成 Python 列表。

                >>> link = Link(1, Link(2, Link(3, Link(4))))
                >>> link_to_list(link)
                [1, 2, 3, 4]
                >>> link_to_list(Link.empty)
                []
                """
                if link is Link.empty:
                    return []
                return [link.first] + link_to_list(link.rest)
            '''
        ),
        hidden_tests="""
            >>> link_to_list(Link(5))
            [5]
            >>> link_to_list(Link('a', Link('b')))
            ['a', 'b']
        """,
        hints=[
            "空链表对应空列表 []。",
            "[link.first] + （剩余链表转换成的列表）。",
        ],
        trace="lst = link_to_list(Link(1, Link(2, Link(3))))",
    ),
    Exercise(
        id="store_digits",
        topic="link",
        title="数字存入链表 store_digits",
        difficulty=2,
        function="store_digits",
        concepts=["构建链表", "从后往前"],
        description=_code(
            """
            实现 `store_digits(n)`：返回一个链表，按顺序存放正整数 `n` 的各位数字。

            提示：用 `n % 10` 取出的是**最后一位**，想想如何从后往前构建链表。
            """
        ),
        starter=_code(
            '''
            def store_digits(n):
                """把 n 的每一位按顺序存入链表。

                >>> s = store_digits(1)
                >>> s
                Link(1)
                >>> store_digits(2345)
                Link(2, Link(3, Link(4, Link(5))))
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def store_digits(n):
                """把 n 的每一位按顺序存入链表。

                >>> s = store_digits(1)
                >>> s
                Link(1)
                >>> store_digits(2345)
                Link(2, Link(3, Link(4, Link(5))))
                """
                result = Link.empty
                while n > 0:
                    result = Link(n % 10, result)
                    n = n // 10
                return result
            '''
        ),
        hidden_tests="""
            >>> store_digits(876)
            Link(8, Link(7, Link(6)))
            >>> store_digits(2000)
            Link(2, Link(0, Link(0, Link(0))))
            >>> isinstance(store_digits(9), Link)
            True
        """,
        hints=[
            "从 result = Link.empty 开始，每次把最后一位放到链表最前面：Link(n % 10, result)。",
            "也可以用递归 + 辅助函数实现，但循环版本更直接。",
        ],
        trace="s = store_digits(345)",
    ),
    Exercise(
        id="every_other",
        topic="link",
        title="隔一个删一个 every_other",
        difficulty=2,
        function="every_other",
        concepts=["修改链表 mutation", "rest 指针"],
        description=_code(
            """
            实现 `every_other(s)`：**原地修改**链表 `s`，删除所有奇数下标（第 1、3、5…个）的元素。函数不返回任何值。

            用环境图观察：修改 `s.rest` 时，箭头是如何改变指向的。
            """
        ),
        starter=_code(
            '''
            def every_other(s):
                """原地删除链表中所有奇数下标的元素。

                >>> s = Link(1, Link(2, Link(3, Link(4))))
                >>> every_other(s)
                >>> s
                Link(1, Link(3))
                >>> odd_length = Link(5, Link(3, Link(1)))
                >>> every_other(odd_length)
                >>> odd_length
                Link(5, Link(1))
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def every_other(s):
                """原地删除链表中所有奇数下标的元素。

                >>> s = Link(1, Link(2, Link(3, Link(4))))
                >>> every_other(s)
                >>> s
                Link(1, Link(3))
                >>> odd_length = Link(5, Link(3, Link(1)))
                >>> every_other(odd_length)
                >>> odd_length
                Link(5, Link(1))
                """
                if s is Link.empty or s.rest is Link.empty:
                    return
                s.rest = s.rest.rest
                every_other(s.rest)
            '''
        ),
        hidden_tests="""
            >>> singleton = Link(4)
            >>> every_other(singleton)
            >>> singleton
            Link(4)
            >>> t = Link(0, Link(1, Link(2, Link(3, Link(4, Link(5))))))
            >>> every_other(t)
            >>> t
            Link(0, Link(2, Link(4)))
        """,
        hints=[
            "如果 s 为空或只有一个元素，什么都不用做。",
            "让 s.rest 跳过下一个节点：s.rest = s.rest.rest，然后对新的 s.rest 递归。",
        ],
        trace="s = Link(1, Link(2, Link(3, Link(4))))\nevery_other(s)",
    ),
    Exercise(
        id="insert",
        topic="link",
        title="插入元素 insert",
        difficulty=2,
        function="insert",
        concepts=["修改链表 mutation", "IndexError"],
        description=_code(
            """
            实现 `insert(link, value, index)`：在链表 `link` 的下标 `index` 处**原地**插入 `value`。

            如果 `index` 超出范围（大于等于链表长度），抛出 `IndexError`。

            技巧：在下标 0 插入时，不能让外面的变量指向新节点——那就把 `value` 放进当前节点，再把原来的 `first` 往后挪。
            """
        ),
        starter=_code(
            '''
            def insert(link, value, index):
                """在链表的 index 位置插入 value。

                >>> link = Link(1, Link(2, Link(3)))
                >>> insert(link, 9001, 0)
                >>> print(link)
                <9001 1 2 3>
                >>> insert(link, 100, 2)
                >>> print(link)
                <9001 1 100 2 3>
                >>> insert(link, 4, 5)
                Traceback (most recent call last):
                    ...
                IndexError
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def insert(link, value, index):
                """在链表的 index 位置插入 value。

                >>> link = Link(1, Link(2, Link(3)))
                >>> insert(link, 9001, 0)
                >>> print(link)
                <9001 1 2 3>
                >>> insert(link, 100, 2)
                >>> print(link)
                <9001 1 100 2 3>
                >>> insert(link, 4, 5)
                Traceback (most recent call last):
                    ...
                IndexError
                """
                if index == 0:
                    link.rest = Link(link.first, link.rest)
                    link.first = value
                elif link.rest is Link.empty:
                    raise IndexError
                else:
                    insert(link.rest, value, index - 1)
            '''
        ),
        hidden_tests="""
            >>> s = Link(1)
            >>> insert(s, 2, 0)
            >>> s
            Link(2, Link(1))
            >>> insert(s, 3, 1)
            >>> s
            Link(2, Link(3, Link(1)))
            >>> insert(Link(1), 2, 1)
            Traceback (most recent call last):
                ...
            IndexError
        """,
        hints=[
            "index == 0 时：先复制当前节点到后面 link.rest = Link(link.first, link.rest)，再修改 link.first。",
            "否则对 link.rest 递归，index 减 1；如果已经没有 rest 了，raise IndexError。",
        ],
        trace="link = Link(1, Link(2, Link(3)))\ninsert(link, 100, 1)",
    ),
    Exercise(
        id="duplicate_link",
        topic="link",
        title="复制节点 duplicate_link",
        difficulty=2,
        function="duplicate_link",
        concepts=["修改链表 mutation", "避免无限循环"],
        description=_code(
            """
            实现 `duplicate_link(lnk, val)`：**原地修改**链表，把每个 `first` 等于 `val` 的节点复制一份（紧跟在原节点后面）。

            小心：复制出来的新节点 `first` 也等于 `val`，如果不跳过它，会无限复制下去！
            """
        ),
        starter=_code(
            '''
            def duplicate_link(lnk, val):
                """把链表中所有值为 val 的节点复制一份。

                >>> x = Link(5, Link(4, Link(3)))
                >>> duplicate_link(x, 5)
                >>> x
                Link(5, Link(5, Link(4, Link(3))))
                >>> y = Link(2, Link(4, Link(6, Link(8))))
                >>> duplicate_link(y, 10)
                >>> y
                Link(2, Link(4, Link(6, Link(8))))
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def duplicate_link(lnk, val):
                """把链表中所有值为 val 的节点复制一份。

                >>> x = Link(5, Link(4, Link(3)))
                >>> duplicate_link(x, 5)
                >>> x
                Link(5, Link(5, Link(4, Link(3))))
                >>> y = Link(2, Link(4, Link(6, Link(8))))
                >>> duplicate_link(y, 10)
                >>> y
                Link(2, Link(4, Link(6, Link(8))))
                """
                if lnk is Link.empty:
                    return
                if lnk.first == val:
                    remaining = lnk.rest
                    lnk.rest = Link(val, remaining)
                    duplicate_link(remaining, val)
                else:
                    duplicate_link(lnk.rest, val)
            '''
        ),
        hidden_tests="""
            >>> z = Link(1, Link(2, Link(2, Link(3))))
            >>> duplicate_link(z, 2)
            >>> z
            Link(1, Link(2, Link(2, Link(2, Link(2, Link(3))))))
            >>> w = Link(7)
            >>> duplicate_link(w, 7)
            >>> w
            Link(7, Link(7))
        """,
        hints=[
            "遇到 first == val 的节点时，在它后面插入 Link(val, 原来的 rest)。",
            "插入后，从“原来的 rest”继续递归，跳过刚插入的新节点。",
        ],
        trace="x = Link(1, Link(2, Link(3)))\nduplicate_link(x, 2)",
    ),
    Exercise(
        id="deep_map_link",
        topic="link",
        title="嵌套映射 deep_map_link",
        difficulty=3,
        function="deep_map_link",
        concepts=["嵌套链表", "isinstance", "非破坏性"],
        constraints=[RECURSIVE],
        description=_code(
            """
            链表的元素本身也可以是链表。实现 `deep_map_link(f, s)`：返回一个**新**链表，结构与 `s` 相同，但每个非链表元素 `x` 都被替换为 `f(x)`。

            不要修改原链表。用 `isinstance(x, Link)` 判断一个元素是否为链表。
            """
        ),
        starter=_code(
            '''
            def deep_map_link(f, s):
                """返回把 f 应用到 s（含嵌套链表）中每个元素后得到的新链表。

                >>> s = Link(1, Link(Link(2, Link(3)), Link(4)))
                >>> deep_map_link(lambda x: x * x, s)
                Link(1, Link(Link(4, Link(9)), Link(16)))
                >>> s
                Link(1, Link(Link(2, Link(3)), Link(4)))
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def deep_map_link(f, s):
                """返回把 f 应用到 s（含嵌套链表）中每个元素后得到的新链表。

                >>> s = Link(1, Link(Link(2, Link(3)), Link(4)))
                >>> deep_map_link(lambda x: x * x, s)
                Link(1, Link(Link(4, Link(9)), Link(16)))
                >>> s
                Link(1, Link(Link(2, Link(3)), Link(4)))
                """
                if s is Link.empty:
                    return s
                if isinstance(s.first, Link):
                    first = deep_map_link(f, s.first)
                else:
                    first = f(s.first)
                return Link(first, deep_map_link(f, s.rest))
            '''
        ),
        hidden_tests="""
            >>> deep_map_link(lambda x: x + 1, Link.empty) is Link.empty
            True
            >>> deep_map_link(str, Link(Link(Link(1)), Link(2)))
            Link(Link(Link('1')), Link('2'))
        """,
        hints=[
            "空链表映射后仍是空链表。",
            "处理 first：如果它是 Link 就递归 deep_map_link(f, s.first)，否则 f(s.first)。",
            "rest 部分同样递归，最后用 Link(新 first, 新 rest) 组装。",
        ],
        trace="s = Link(1, Link(Link(2, Link(3)), Link(4)))\nresult = deep_map_link(lambda x: x * 10, s)",
    ),
    # ------------------------------------------------------------ trees
    Exercise(
        id="sum_labels",
        topic="tree",
        title="标签求和 sum_labels",
        difficulty=1,
        function="sum_labels",
        concepts=["树递归", "for b in t.branches"],
        constraints=[RECURSIVE],
        description=_code(
            """
            实现 `sum_labels(t)`：返回树 `t` 中所有节点 label 之和。

            树的标准递归模板：处理当前节点 `t.label`，再对每个分支 `b in t.branches` 递归。
            """
        ),
        starter=_code(
            '''
            def sum_labels(t):
                """返回树中所有 label 的和。

                >>> t = Tree(1, [Tree(2, [Tree(4)]), Tree(3)])
                >>> sum_labels(t)
                10
                >>> sum_labels(Tree(5))
                5
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def sum_labels(t):
                """返回树中所有 label 的和。

                >>> t = Tree(1, [Tree(2, [Tree(4)]), Tree(3)])
                >>> sum_labels(t)
                10
                >>> sum_labels(Tree(5))
                5
                """
                return t.label + sum([sum_labels(b) for b in t.branches])
            '''
        ),
        hidden_tests="""
            >>> sum_labels(Tree(0, [Tree(-1), Tree(1, [Tree(10), Tree(20)])]))
            30
        """,
        hints=[
            "叶子节点没有分支，sum([]) == 0，所以甚至不需要单独写基本情况。",
            "t.label + sum([sum_labels(b) for b in t.branches])",
        ],
        trace="t = Tree(1, [Tree(2, [Tree(4)]), Tree(3)])\ntotal = sum_labels(t)",
    ),
    Exercise(
        id="height",
        topic="tree",
        title="树的高度 height",
        difficulty=1,
        function="height",
        concepts=["树递归", "max"],
        constraints=[RECURSIVE],
        description=_code(
            """
            树的高度 = 从根到最远叶子的边数。只有一个节点的树高度为 0。

            实现 `height(t)`。
            """
        ),
        starter=_code(
            '''
            def height(t):
                """返回树的高度。

                >>> height(Tree(1))
                0
                >>> t = Tree(3, [Tree(5, [Tree(1)]), Tree(2)])
                >>> height(t)
                2
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def height(t):
                """返回树的高度。

                >>> height(Tree(1))
                0
                >>> t = Tree(3, [Tree(5, [Tree(1)]), Tree(2)])
                >>> height(t)
                2
                """
                if t.is_leaf():
                    return 0
                return 1 + max([height(b) for b in t.branches])
            '''
        ),
        hidden_tests="""
            >>> height(Tree(1, [Tree(2, [Tree(3, [Tree(4)])]), Tree(5)]))
            3
            >>> height(Tree(1, [Tree(2), Tree(3), Tree(4)]))
            1
        """,
        hints=[
            "叶子的高度是 0。",
            "非叶子：1 + 所有分支高度的最大值。注意 max([]) 会报错，所以叶子必须单独处理。",
        ],
        trace="t = Tree(3, [Tree(5, [Tree(1)]), Tree(2)])\nh = height(t)",
    ),
    Exercise(
        id="berry_finder",
        topic="tree",
        title="寻找浆果 berry_finder",
        difficulty=1,
        function="berry_finder",
        concepts=["树搜索", "提前返回"],
        constraints=[RECURSIVE],
        description=_code(
            """
            松鼠 Scrat 在树上找浆果。实现 `berry_finder(t)`：如果树中有某个节点的 label 是 `'berry'`，返回 `True`，否则返回 `False`。
            """
        ),
        starter=_code(
            '''
            def berry_finder(t):
                """如果树中含有 'berry' 则返回 True。

                >>> scrat = Tree('berry')
                >>> berry_finder(scrat)
                True
                >>> sproul = Tree('roots', [Tree('branch1', [Tree('leaf'), Tree('berry')]), Tree('branch2')])
                >>> berry_finder(sproul)
                True
                >>> numbers = Tree(1, [Tree(2), Tree(3, [Tree(4), Tree(5)]), Tree(6, [Tree(7)])])
                >>> berry_finder(numbers)
                False
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def berry_finder(t):
                """如果树中含有 'berry' 则返回 True。

                >>> scrat = Tree('berry')
                >>> berry_finder(scrat)
                True
                >>> sproul = Tree('roots', [Tree('branch1', [Tree('leaf'), Tree('berry')]), Tree('branch2')])
                >>> berry_finder(sproul)
                True
                >>> numbers = Tree(1, [Tree(2), Tree(3, [Tree(4), Tree(5)]), Tree(6, [Tree(7)])])
                >>> berry_finder(numbers)
                False
                """
                if t.label == 'berry':
                    return True
                for b in t.branches:
                    if berry_finder(b):
                        return True
                return False
            '''
        ),
        hidden_tests="""
            >>> berry_finder(Tree(1, [Tree('berry', [Tree('not berry')])]))
            True
            >>> berry_finder(Tree('not berry'))
            False
        """,
        hints=[
            "先检查当前节点的 label。",
            "只要有一个分支里找到浆果，就可以立刻 return True；全部分支都找不到才 return False。",
        ],
        trace="t = Tree('roots', [Tree('leaf'), Tree('branch', [Tree('berry')])])\nfound = berry_finder(t)",
    ),
    Exercise(
        id="square_tree",
        topic="tree",
        title="平方树 square_tree",
        difficulty=2,
        function="square_tree",
        concepts=["修改树 mutation"],
        constraints=[RECURSIVE],
        description=_code(
            """
            实现 `square_tree(t)`：**原地修改**树 `t`，把每个节点的 label 替换为它的平方。函数不返回值。
            """
        ),
        starter=_code(
            '''
            def square_tree(t):
                """原地把树中每个 label 平方。

                >>> t = Tree(1, [Tree(3, [Tree(5)]), Tree(7)])
                >>> square_tree(t)
                >>> t
                Tree(1, [Tree(9, [Tree(25)]), Tree(49)])
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def square_tree(t):
                """原地把树中每个 label 平方。

                >>> t = Tree(1, [Tree(3, [Tree(5)]), Tree(7)])
                >>> square_tree(t)
                >>> t
                Tree(1, [Tree(9, [Tree(25)]), Tree(49)])
                """
                t.label = t.label ** 2
                for b in t.branches:
                    square_tree(b)
            '''
        ),
        hidden_tests="""
            >>> leaf = Tree(-4)
            >>> square_tree(leaf)
            >>> leaf.label
            16
            >>> t2 = Tree(2, [Tree(2, [Tree(2)])])
            >>> square_tree(t2)
            >>> t2
            Tree(4, [Tree(4, [Tree(4)])])
        """,
        hints=[
            "修改当前节点：t.label = t.label ** 2。",
            "对每个分支递归调用 square_tree——不需要返回任何东西。",
        ],
        trace="t = Tree(1, [Tree(3, [Tree(5)]), Tree(7)])\nsquare_tree(t)",
    ),
    Exercise(
        id="max_path_sum",
        topic="tree",
        title="最大路径和 max_path_sum",
        difficulty=2,
        function="max_path_sum",
        concepts=["树递归", "根到叶路径"],
        constraints=[RECURSIVE],
        description=_code(
            """
            实现 `max_path_sum(t)`：在所有**从根到叶子**的路径中，返回 label 之和的最大值。
            """
        ),
        starter=_code(
            '''
            def max_path_sum(t):
                """返回根到叶路径上 label 之和的最大值。

                >>> t = Tree(1, [Tree(5, [Tree(1), Tree(3)]), Tree(10)])
                >>> max_path_sum(t)
                11
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def max_path_sum(t):
                """返回根到叶路径上 label 之和的最大值。

                >>> t = Tree(1, [Tree(5, [Tree(1), Tree(3)]), Tree(10)])
                >>> max_path_sum(t)
                11
                """
                if t.is_leaf():
                    return t.label
                return t.label + max([max_path_sum(b) for b in t.branches])
            '''
        ),
        hidden_tests="""
            >>> t2 = Tree(5, [Tree(4, [Tree(1), Tree(3)]), Tree(2, [Tree(10), Tree(3)])])
            >>> max_path_sum(t2)
            17
            >>> max_path_sum(Tree(42))
            42
        """,
        hints=[
            "叶子：路径和就是它自己的 label。",
            "非叶子：t.label + 各分支最大路径和中的最大值。",
        ],
        trace="t = Tree(1, [Tree(5, [Tree(1), Tree(3)]), Tree(10)])\nbest = max_path_sum(t)",
    ),
    Exercise(
        id="find_path",
        topic="tree",
        title="查找路径 find_path",
        difficulty=2,
        function="find_path",
        concepts=["树搜索", "返回 None 的含义"],
        constraints=[RECURSIVE],
        description=_code(
            """
            实现 `find_path(t, x)`：返回从根到 label 为 `x` 的节点的路径（label 组成的列表）。如果 `x` 不在树中，返回 `None`。

            你可以假设树中的 label 各不相同。
            """
        ),
        starter=_code(
            '''
            def find_path(t, x):
                """返回从根到 x 的路径；找不到时返回 None。

                >>> t = Tree(2, [Tree(7, [Tree(3), Tree(6, [Tree(5), Tree(11)])]), Tree(15)])
                >>> find_path(t, 5)
                [2, 7, 6, 5]
                >>> find_path(t, 10)  # 返回 None，交互式解释器不显示
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def find_path(t, x):
                """返回从根到 x 的路径；找不到时返回 None。

                >>> t = Tree(2, [Tree(7, [Tree(3), Tree(6, [Tree(5), Tree(11)])]), Tree(15)])
                >>> find_path(t, 5)
                [2, 7, 6, 5]
                >>> find_path(t, 10)  # 返回 None，交互式解释器不显示
                """
                if t.label == x:
                    return [t.label]
                for b in t.branches:
                    path = find_path(b, x)
                    if path:
                        return [t.label] + path
                return None
            '''
        ),
        hidden_tests="""
            >>> t = Tree(2, [Tree(7, [Tree(3), Tree(6, [Tree(5), Tree(11)])]), Tree(15)])
            >>> find_path(t, 2)
            [2]
            >>> find_path(t, 15)
            [2, 15]
            >>> find_path(t, 11)
            [2, 7, 6, 11]
            >>> print(find_path(t, 100))
            None
        """,
        hints=[
            "如果当前节点就是 x，路径就是 [t.label]。",
            "否则在每个分支中查找；一旦某个分支返回了路径（不是 None），就在前面加上 t.label 并返回。",
        ],
        trace="t = Tree(2, [Tree(7, [Tree(3), Tree(6)]), Tree(15)])\npath = find_path(t, 6)",
    ),
    Exercise(
        id="prune_small",
        topic="tree",
        title="修剪小分支 prune_small",
        difficulty=3,
        function="prune_small",
        concepts=["修改树 mutation", "列表 remove", "max(key=...)"],
        constraints=[RECURSIVE],
        description=_code(
            """
            实现 `prune_small(t, n)`：**原地修改**树，使每个节点最多只保留 `n` 个分支——保留 label **最小**的那些。

            提示：当分支太多时，反复找出 label 最大的分支并删除；然后对剩下的分支递归。
            """
        ),
        starter=_code(
            '''
            def prune_small(t, n):
                """原地修剪树，每个节点只保留 label 最小的 n 个分支。

                >>> t1 = Tree(6)
                >>> prune_small(t1, 2)
                >>> t1
                Tree(6)
                >>> t2 = Tree(6, [Tree(3), Tree(4)])
                >>> prune_small(t2, 1)
                >>> t2
                Tree(6, [Tree(3)])
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def prune_small(t, n):
                """原地修剪树，每个节点只保留 label 最小的 n 个分支。

                >>> t1 = Tree(6)
                >>> prune_small(t1, 2)
                >>> t1
                Tree(6)
                >>> t2 = Tree(6, [Tree(3), Tree(4)])
                >>> prune_small(t2, 1)
                >>> t2
                Tree(6, [Tree(3)])
                """
                while len(t.branches) > n:
                    largest = max(t.branches, key=lambda x: x.label)
                    t.branches.remove(largest)
                for b in t.branches:
                    prune_small(b, n)
            '''
        ),
        hidden_tests="""
            >>> t3 = Tree(6, [Tree(1), Tree(3, [Tree(1), Tree(2), Tree(3)]), Tree(5, [Tree(3), Tree(4)])])
            >>> prune_small(t3, 2)
            >>> t3
            Tree(6, [Tree(1), Tree(3, [Tree(1), Tree(2)])])
            >>> t4 = Tree(1, [Tree(9), Tree(8), Tree(7)])
            >>> prune_small(t4, 0)
            >>> t4
            Tree(1)
        """,
        hints=[
            "while len(t.branches) > n: 找出 label 最大的分支并从 t.branches 中删除。",
            "max(t.branches, key=lambda b: b.label) 可以找到 label 最大的分支。",
            "修剪完当前节点后，再对每个剩余分支递归。",
        ],
        trace="t = Tree(6, [Tree(1), Tree(3, [Tree(1), Tree(2), Tree(3)]), Tree(5)])\nprune_small(t, 2)",
    ),
    Exercise(
        id="count_leaves",
        topic="tree",
        title="数叶子（函数式树 ADT）count_leaves",
        difficulty=1,
        function="count_leaves",
        concepts=["数据抽象", "tree / label / branches"],
        constraints=[RECURSIVE],
        description=_code(
            """
            CS61A 前半学期使用**函数式树 ADT**：`tree(label, branches)` 构造，`label(t)`、`branches(t)`、`is_leaf(t)` 选择。
            这些函数已经内置在平台中。

            实现 `count_leaves(t)`：返回树中叶子的个数。**只通过 ADT 函数访问树**，不要直接用下标（抽象屏障！）。
            """
        ),
        starter=_code(
            '''
            def count_leaves(t):
                """返回树 t 的叶子数（t 是函数式 tree ADT）。

                >>> t = tree(1, [tree(2), tree(3, [tree(4), tree(5)])])
                >>> count_leaves(t)
                3
                >>> count_leaves(tree(7))
                1
                """
                "*** YOUR CODE HERE ***"
            '''
        ),
        solution=_code(
            '''
            def count_leaves(t):
                """返回树 t 的叶子数（t 是函数式 tree ADT）。

                >>> t = tree(1, [tree(2), tree(3, [tree(4), tree(5)])])
                >>> count_leaves(t)
                3
                >>> count_leaves(tree(7))
                1
                """
                if is_leaf(t):
                    return 1
                return sum([count_leaves(b) for b in branches(t)])
            '''
        ),
        hidden_tests="""
            >>> count_leaves(tree(1, [tree(2, [tree(3, [tree(4)])])]))
            1
            >>> count_leaves(tree(0, [tree(1), tree(2), tree(3), tree(4)]))
            4
        """,
        hints=[
            "叶子本身算 1 个。",
            "非叶子：所有分支叶子数之和 sum([count_leaves(b) for b in branches(t)])。",
        ],
        trace="t = tree(1, [tree(2), tree(3, [tree(4)])])\nn = count_leaves(t)",
    ),
]

EXERCISES_BY_ID = {e.id: e for e in EXERCISES}


def list_exercises() -> list[dict]:
    return [e.summary() for e in EXERCISES]


def get_exercise(exercise_id: str) -> Exercise | None:
    return EXERCISES_BY_ID.get(exercise_id)
