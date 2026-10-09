""""What Would Python Display?" (WWPD) quizzes, CS61A style.

Answer conventions (same as CS61A's ok tool):

* type exactly what the interactive interpreter would show;
* ``Error`` if evaluating the expression raises an error;
* ``Function`` if the value is a function;
* if the expression prints several lines, type them all (one per line).

The expected answers are stored here and verified against real Python by the
test-suite (``tests/test_quizzes.py``).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Quiz:
    id: str
    topic: str
    setup: str
    expression: str
    answer: str
    explanation: str

    def public(self) -> dict:
        return {
            "id": self.id,
            "topic": self.topic,
            "setup": self.setup,
            "expression": self.expression,
        }


QUIZZES: list[Quiz] = [
    Quiz(
        "rec-sum",
        "recursion",
        "def f(n):\n    if n == 0:\n        return 0\n    return n + f(n - 1)",
        "f(4)",
        "10",
        "f(4) = 4 + f(3) = 4 + 3 + f(2) = … = 4 + 3 + 2 + 1 + 0 = 10。",
    ),
    Quiz(
        "rec-cascade",
        "recursion",
        "def cascade(n):\n    if n < 10:\n        print(n)\n    else:\n        print(n)\n        cascade(n // 10)\n        print(n)",
        "cascade(123)",
        "123\n12\n1\n12\n123",
        "递归调用之前的 print 在“下降”时执行，之后的 print 在“返回”时执行，所以输出呈对称形状。",
    ),
    Quiz(
        "rec-none",
        "recursion",
        "def g(n):\n    if n > 0:\n        g(n - 1)",
        "print(g(3))",
        "None",
        "g 从不 return 任何值，所以返回 None；递归调用的结果被丢弃了。",
    ),
    Quiz(
        "rec-order",
        "recursion",
        "def h(n):\n    if n == 0:\n        return 'done'\n    print(n)\n    return h(n - 1)",
        "h(2)",
        "2\n1\n'done'",
        "先打印 2 和 1，最后交互式解释器显示返回值 'done'（字符串带引号）。",
    ),
    Quiz(
        "rec-infinite",
        "recursion",
        "def bad(n):\n    return bad(n - 1)",
        "bad(3)",
        "Error",
        "没有基本情况，递归永不停止，最终抛出 RecursionError。",
    ),
    Quiz(
        "link-rest",
        "link",
        "lnk = Link(1, Link(2, Link(3)))",
        "lnk.rest.first",
        "2",
        "lnk.rest 是 Link(2, Link(3))，它的 first 是 2。",
    ),
    Quiz(
        "link-empty",
        "link",
        "lnk = Link(1, Link(2, Link(3)))",
        "lnk.rest.rest.rest is Link.empty",
        "True",
        "最后一个节点 Link(3) 的 rest 默认就是 Link.empty。",
    ),
    Quiz(
        "link-str",
        "link",
        "lnk = Link(1, Link(2, Link(3)))",
        "print(lnk)",
        "<1 2 3>",
        "print 调用 __str__，Link 的 __str__ 用尖括号显示元素。",
    ),
    Quiz(
        "link-repr",
        "link",
        "lnk = Link(1, Link(2, Link(3)))",
        "lnk.rest",
        "Link(2, Link(3))",
        "交互式解释器显示 repr，Link 的 __repr__ 形如 Link(2, Link(3))。",
    ),
    Quiz(
        "link-error",
        "link",
        "lnk = Link(1, Link(2, Link(3)))",
        "lnk.rest.rest.rest.first",
        "Error",
        "lnk.rest.rest.rest 是 Link.empty（一个空元组），它没有 first 属性 → AttributeError。",
    ),
    Quiz(
        "link-mutate",
        "link",
        "a = Link(1, Link(2))\nb = a.rest\nb.first = 5",
        "a",
        "Link(1, Link(5))",
        "b 和 a.rest 指向同一个对象，修改 b.first 就修改了 a 的第二个元素。用环境图看看两个箭头！",
    ),
    Quiz(
        "tree-label",
        "tree",
        "t = Tree(1, [Tree(2), Tree(3, [Tree(4)])])",
        "t.branches[1].label",
        "3",
        "t.branches 是 [Tree(2), Tree(3, [Tree(4)])]，下标 1 的 label 是 3。",
    ),
    Quiz(
        "tree-leaf",
        "tree",
        "t = Tree(1, [Tree(2), Tree(3, [Tree(4)])])",
        "t.branches[0].is_leaf()",
        "True",
        "Tree(2) 没有分支，是叶子。",
    ),
    Quiz(
        "tree-labels",
        "tree",
        "t = Tree(1, [Tree(2), Tree(3, [Tree(4)])])",
        "[b.label for b in t.branches]",
        "[2, 3]",
        "列表推导式只遍历直接分支，不会进入更深的层次。",
    ),
    Quiz(
        "tree-print",
        "tree",
        "t = Tree(1, [Tree(2), Tree(3, [Tree(4)])])",
        "print(t)",
        "1\n  2\n  3\n    4",
        "Tree 的 __str__ 每深一层缩进两个空格。",
    ),
    Quiz(
        "tree-method",
        "tree",
        "t = Tree(1, [Tree(2)])",
        "t.branches()",
        "Error",
        "branches 是一个列表属性，不是方法；调用列表会抛出 TypeError: 'list' object is not callable。",
    ),
    Quiz(
        "tree-adt",
        "tree",
        "t = tree(3, [tree(4), tree(5)])",
        "label(branches(t)[1])",
        "5",
        "函数式 ADT：branches(t) 返回分支列表，下标 1 是 tree(5)，label 是 5。",
    ),
]

QUIZZES_BY_ID = {q.id: q for q in QUIZZES}


def normalize(text: str) -> str:
    lines = [line.rstrip() for line in text.strip().replace("\r\n", "\n").split("\n")]
    return "\n".join(line for line in lines if line != "")


def check_answer(quiz: Quiz, answer: str) -> dict:
    given = normalize(answer)
    expected = normalize(quiz.answer)
    correct = given == expected
    if not correct and expected in ("Error", "Function"):
        correct = given.lower() == expected.lower()
    if not correct:
        # Accept a different quote style for string answers: 'done' vs "done".
        correct = given.replace('"', "'") == expected
    return {"correct": correct, "answer": quiz.answer, "explanation": quiz.explanation}
