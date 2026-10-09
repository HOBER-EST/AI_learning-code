"""CS61A helpers made available to every student program.

These names are injected into the student's builtins (not their globals), so
they can be used without importing them, and they do not clutter the Global
frame in environment diagrams. A student may still define their own ``Link``
or ``Tree`` class, which simply shadows the version here.
"""


class Link:
    """A linked list.

    >>> s = Link(1, Link(2, Link(3)))
    >>> s.first
    1
    >>> s.rest
    Link(2, Link(3))
    >>> print(s)
    <1 2 3>
    """

    empty = ()

    def __init__(self, first, rest=empty):
        assert rest is Link.empty or isinstance(rest, Link)
        self.first = first
        self.rest = rest

    def __repr__(self):
        if self.rest is not Link.empty:
            rest_repr = ", " + repr(self.rest)
        else:
            rest_repr = ""
        return "Link(" + repr(self.first) + rest_repr + ")"

    def __str__(self):
        string = "<"
        while self.rest is not Link.empty:
            string += str(self.first) + " "
            self = self.rest
        return string + str(self.first) + ">"


class Tree:
    """A tree with a label and a list of branches.

    >>> t = Tree(1, [Tree(2), Tree(3, [Tree(4)])])
    >>> t.label
    1
    >>> t.branches[1].branches[0].label
    4
    >>> t.branches[0].is_leaf()
    True
    """

    def __init__(self, label, branches=[]):
        for b in branches:
            assert isinstance(b, Tree)
        self.label = label
        self.branches = list(branches)

    def is_leaf(self):
        return not self.branches

    def __repr__(self):
        if self.branches:
            branch_str = ", " + repr(self.branches)
        else:
            branch_str = ""
        return "Tree({0}{1})".format(repr(self.label), branch_str)

    def __str__(self):
        def print_tree(t, indent=0):
            tree_str = "  " * indent + str(t.label) + "\n"
            for b in t.branches:
                tree_str += print_tree(b, indent + 1)
            return tree_str

        return print_tree(self).rstrip()


# --- The functional tree ADT used in the first half of CS61A -------------


def tree(label, branches=[]):
    """Construct a tree with the given label value and a list of branches."""
    for branch in branches:
        assert is_tree(branch), "branches must be trees"
    return [label] + list(branches)


def label(tree):
    """Return the label value of a tree."""
    return tree[0]


def branches(tree):
    """Return the list of branches of the given tree."""
    return tree[1:]


def is_tree(tree):
    """Returns True if the given tree is a tree, and False otherwise."""
    if type(tree) != list or len(tree) < 1:
        return False
    for branch in branches(tree):
        if not is_tree(branch):
            return False
    return True


def is_leaf(tree):
    """Returns True if the given tree's list of branches is empty."""
    return not branches(tree)


def print_tree(t, indent=0):
    """Print a representation of this tree in which each label is indented
    by two spaces times its depth from the root."""
    print("  " * indent + str(label(t)))
    for b in branches(t):
        print_tree(b, indent + 1)


PRELUDE_NAMES = (
    "Link",
    "Tree",
    "tree",
    "label",
    "branches",
    "is_tree",
    "is_leaf",
    "print_tree",
)


def _disabled_input(prompt=""):
    raise RuntimeError("input() 在本平台中不可用：请把数据直接写在代码里")


def make_builtins():
    """Return a fresh builtins dict that also exposes the CS61A helpers."""
    import builtins

    namespace = dict(vars(builtins))
    module_globals = globals()
    for name in PRELUDE_NAMES:
        namespace[name] = module_globals[name]
    namespace["input"] = _disabled_input
    return namespace
