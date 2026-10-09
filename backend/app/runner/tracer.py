"""Step-by-step execution tracer that produces CS61A-style environment diagrams.

The tracer runs student code under ``sys.settrace`` and records a snapshot of
the program state at every ``call``/``line``/``return``/``exception`` event in
the student's file. Each snapshot contains:

* every frame created so far (CS61A diagrams keep exited frames around, along
  with their return values), with its ``[parent=...]`` frame;
* the heap objects reachable from those frames (lists, dicts, functions,
  ``Link`` and ``Tree`` instances, ...), referenced by stable ids;
* the program output so far.

It also builds a recursion call tree (one node per function call) that the
frontend animates in step with the diagram.

This module is executed inside the sandboxed child process.
"""

from __future__ import annotations

import inspect
import io
import linecache
import sys
import traceback
import types
from collections import deque

STUDENT_FILE = "<student>"

MAX_STEPS_DEFAULT = 1000
MAX_HEAP_OBJECTS = 300
MAX_ITEMS = 60
MAX_STR = 120
MAX_STDOUT = 20_000

_PRIMITIVE_TYPES = (int, float, complex, bool, type(None), str)
_HIDDEN_CODE_NAMES = {"<genexpr>", "<listcomp>", "<dictcomp>", "<setcomp>"}


class StopTracing(BaseException):
    """Raised inside student code to abort execution once the step budget is spent."""


def _truncate(text: str, limit: int = MAX_STR) -> str:
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _prim_repr(value) -> str:
    if isinstance(value, int) and not isinstance(value, bool) and value.bit_length() > 200:
        return "<很大的整数>"
    return _truncate(repr(value))


def is_link(value) -> bool:
    return type(value).__name__ == "Link" and hasattr(value, "first") and hasattr(value, "rest")


def is_tree(value) -> bool:
    return (
        type(value).__name__ == "Tree"
        and hasattr(value, "label")
        and isinstance(getattr(value, "branches", None), list)
    )


def _is_link_empty(owner, value) -> bool:
    return value is getattr(type(owner), "empty", object()) or value == ()


def short_repr(value, budget: int = 40) -> str:
    """A compact repr that never calls student-defined ``__repr__`` methods."""
    out: list[str] = []

    def emit(v, depth: int) -> None:
        if sum(len(s) for s in out) > budget:
            return
        if isinstance(v, _PRIMITIVE_TYPES):
            out.append(_prim_repr(v))
        elif depth > 3:
            out.append("…")
        elif is_link(v):
            out.append("Link(")
            emit(v.first, depth + 1)
            if not _is_link_empty(v, v.rest):
                out.append(", ")
                emit(v.rest, depth + 1)
            out.append(")")
        elif is_tree(v):
            out.append("Tree(")
            emit(v.label, depth + 1)
            if v.branches:
                out.append(", [")
                for i, b in enumerate(v.branches):
                    if i:
                        out.append(", ")
                    emit(b, depth + 1)
                out.append("]")
            out.append(")")
        elif isinstance(v, (list, tuple)):
            open_, close = ("[", "]") if isinstance(v, list) else ("(", ")")
            out.append(open_)
            for i, item in enumerate(v):
                if i:
                    out.append(", ")
                emit(item, depth + 1)
                if sum(len(s) for s in out) > budget:
                    break
            if isinstance(v, tuple) and len(v) == 1:
                out.append(",")
            out.append(close)
        elif isinstance(v, types.FunctionType):
            out.append("λ" if v.__name__ == "<lambda>" else v.__name__)
        elif isinstance(v, type):
            out.append(v.__name__)
        else:
            out.append(type(v).__name__ + " 实例")

    emit(value, 0)
    text = "".join(out)
    return _truncate(text, budget + 10)


class FrameRecord:
    __slots__ = (
        "id",
        "num",
        "name",
        "code",
        "parent",
        "frame",
        "snapshot",
        "returned",
        "return_value",
        "raised",
        "pending_exception",
        "caller",
        "depth",
        "call_step",
    )

    def __init__(self, num, frame, parent, caller, depth):
        self.num = num
        self.id = f"f{num}"
        code = frame.f_code
        self.code = code
        self.name = "λ" if code.co_name == "<lambda>" else code.co_name
        self.parent = parent
        self.frame = frame
        self.snapshot = None
        self.returned = False
        self.return_value = None
        self.raised = False
        self.pending_exception = None
        self.caller = caller
        self.depth = depth
        self.call_step = 0

    @property
    def label(self) -> str:
        if self.name == "λ":
            return f"{self.id}: λ <line {self.code.co_firstlineno}>"
        return f"{self.id}: {self.name}"


class Tracer:
    def __init__(self, max_steps: int = MAX_STEPS_DEFAULT):
        self.max_steps = max_steps
        self.steps: list[dict] = []
        self.stdout = io.StringIO()
        self.module_code = None
        self.module_frame = None
        self.globals: dict | None = None
        self.code_parent: dict[int, types.CodeType] = {}
        self.records: list[FrameRecord] = []
        self.live: dict[int, FrameRecord] = {}
        self.func_parent: dict[int, str] = {}
        self.funcs_by_code: dict[int, list] = {}
        self._keepalive: list = []
        self.obj_ids: dict[int, str] = {}
        self.calls: list[dict] = []
        self.truncated = False
        self.stopped = False

    # ------------------------------------------------------------------ setup

    def _index_code(self, code, parent=None) -> None:
        if parent is not None:
            self.code_parent[id(code)] = parent
        for const in code.co_consts:
            if isinstance(const, types.CodeType):
                self._index_code(const, code)

    def _is_transparent(self, code) -> bool:
        """Class bodies and comprehensions do not get frames in CS61A diagrams."""
        if code is self.module_code:
            return False
        if code.co_name in _HIDDEN_CODE_NAMES:
            return True
        return not (code.co_flags & inspect.CO_OPTIMIZED)

    # ------------------------------------------------------- parent lookups

    def _defining_code(self, code):
        parent = self.code_parent.get(id(code))
        while parent is not None and self._is_transparent(parent):
            parent = self.code_parent.get(id(parent))
        return parent

    def _frame_for_code(self, code) -> str:
        if code is None or code is self.module_code:
            return "Global"
        for rec in reversed(list(self.live.values())):
            if rec.code is code:
                return rec.id
        for rec in reversed(self.records):
            if rec.code is code:
                return rec.id
        return "Global"

    def _register_function(self, func) -> str:
        key = id(func)
        if key not in self.func_parent:
            code = func.__code__
            if code.co_filename == STUDENT_FILE:
                parent = self._frame_for_code(self._defining_code(code))
            else:
                parent = "Global"
            self.func_parent[key] = parent
            self.funcs_by_code.setdefault(id(code), []).append(func)
            self._keepalive.append(func)
        return self.func_parent[key]

    def _parent_for_call(self, frame) -> str:
        code = frame.f_code
        candidates = self.funcs_by_code.get(id(code), [])
        if len(candidates) == 1:
            return self.func_parent[id(candidates[0])]
        if candidates:
            if code.co_freevars:
                local_vars = frame.f_locals
                for func in reversed(candidates):
                    cells = func.__closure__ or ()
                    try:
                        if all(
                            name in local_vars and local_vars[name] is cell.cell_contents
                            for name, cell in zip(code.co_freevars, cells)
                        ):
                            return self.func_parent[id(func)]
                    except ValueError:  # empty cell
                        continue
            return self.func_parent[id(candidates[-1])]
        return self._frame_for_code(self._defining_code(code))

    def _visible_caller(self, frame):
        f = frame.f_back
        while f is not None:
            rec = self.live.get(id(f))
            if rec is not None:
                return rec
            f = f.f_back
        return None

    # ---------------------------------------------------------- the hook

    def trace(self, frame, event, arg):
        if self.stopped:
            raise StopTracing()
        code = frame.f_code
        if code.co_filename != STUDENT_FILE:
            return None

        if event == "call":
            if code is self.module_code:
                self.module_frame = frame
                return self.trace
            if self._is_transparent(code):
                return None
            parent = self._parent_for_call(frame)
            caller = self._visible_caller(frame)
            rec = FrameRecord(
                len(self.records) + 1,
                frame,
                parent,
                caller.id if caller else None,
                (caller.depth + 1) if caller else 1,
            )
            rec.call_step = len(self.steps)
            self.records.append(rec)
            self.live[id(frame)] = rec
            self.calls.append(
                {
                    "id": rec.id,
                    "name": rec.name,
                    "label": self._call_label(rec, frame),
                    "parent": rec.caller,
                    "depth": rec.depth,
                    "call_step": rec.call_step,
                    "return_step": None,
                    "ret": None,
                    "status": "active",
                }
            )

        rec = self.live.get(id(frame))
        if frame is not self.module_frame and rec is None:
            return self.trace

        if event == "line" and rec is not None:
            rec.pending_exception = None
        exception_text = None
        if event == "exception":
            exc_type, exc_value, _ = arg
            exception_text = f"{exc_type.__name__}: {exc_value}"
            if rec is not None:
                rec.pending_exception = exception_text
        if event == "return" and rec is not None:
            if rec.pending_exception is not None:
                rec.raised = True
            else:
                rec.returned = True
                rec.return_value = arg

        self._record(frame, event, exception_text)

        if event == "return" and rec is not None:
            self._finish_frame(rec, frame)
        return self.trace

    def _call_label(self, rec: FrameRecord, frame) -> str:
        code = frame.f_code
        nargs = code.co_argcount + code.co_kwonlyargcount
        if code.co_flags & inspect.CO_VARARGS:
            nargs += 1
        if code.co_flags & inspect.CO_VARKEYWORDS:
            nargs += 1
        names = code.co_varnames[:nargs]
        local_vars = frame.f_locals
        parts = []
        for name in names:
            if name == "self" and len(names) > 1:
                continue
            parts.append(short_repr(local_vars.get(name), 30))
        return f"{rec.name}({', '.join(parts)})"

    def _finish_frame(self, rec: FrameRecord, frame) -> None:
        rec.snapshot = self._frame_locals(frame)
        rec.frame = None
        self.live.pop(id(frame), None)
        node = self.calls[rec.num - 1]
        node["return_step"] = len(self.steps) - 1
        if rec.raised:
            node["status"] = "error"
            node["ret"] = rec.pending_exception
        else:
            node["status"] = "returned"
            node["ret"] = short_repr(rec.return_value, 30)
        self._keepalive.append(rec.return_value)

    @staticmethod
    def _frame_locals(frame) -> dict:
        free = set(frame.f_code.co_freevars)
        return {k: v for k, v in frame.f_locals.items() if k not in free}

    # ------------------------------------------------------------ snapshots

    def _record(self, frame, event, exception_text) -> None:
        if len(self.steps) >= self.max_steps:
            self.truncated = True
            self.stopped = True
            raise StopTracing()

        heap: dict[str, dict] = {}
        queue: deque = deque()

        def enc(value):
            return self._encode(value, heap, queue)

        global_vars = [
            [name, enc(value)]
            for name, value in self.globals.items()
            if not (name.startswith("__") and name.endswith("__"))
        ]

        frames = []
        for rec in self.records:
            local_vars = self._frame_locals(rec.frame) if rec.frame is not None else rec.snapshot
            entry = {
                "id": rec.id,
                "label": rec.label,
                "name": rec.name,
                "parent": rec.parent,
                "vars": [[name, enc(value)] for name, value in local_vars.items()],
                "live": rec.frame is not None,
            }
            if rec.returned:
                entry["ret"] = enc(rec.return_value)
            if rec.raised:
                entry["raised"] = True
            frames.append(entry)

        heap_truncated = self._drain(heap, queue)

        stack = ["Global"]
        f = frame
        chain = []
        while f is not None:
            rec = self.live.get(id(f))
            if rec is not None:
                chain.append(rec.id)
            f = f.f_back
        stack.extend(reversed(chain))

        current = self.live.get(id(frame))
        output = self.stdout.getvalue()
        step = {
            "event": event,
            "line": frame.f_lineno,
            "frame": current.id if current else "Global",
            "stack": stack,
            "globals": global_vars,
            "frames": frames,
            "heap": heap,
            "stdout": output[-MAX_STDOUT:],
        }
        if exception_text:
            step["exception"] = exception_text
        if heap_truncated:
            step["heap_truncated"] = True
        self.steps.append(step)

    def _object_id(self, value) -> str:
        key = id(value)
        oid = self.obj_ids.get(key)
        if oid is None:
            oid = f"o{len(self.obj_ids) + 1}"
            self.obj_ids[key] = oid
            self._keepalive.append(value)
        return oid

    def _encode(self, value, heap, queue) -> dict:
        if isinstance(value, _PRIMITIVE_TYPES):
            return {"t": "prim", "v": _prim_repr(value)}
        if type(value) is tuple and not value:
            # Link.empty is (); CS61A diagrams show it inline, not as an object.
            return {"t": "prim", "v": "()"}
        if isinstance(value, types.ModuleType):
            return {"t": "prim", "v": f"<module '{value.__name__}'>"}
        if isinstance(value, type) and value.__module__ == "builtins":
            return {"t": "prim", "v": f"<class '{value.__name__}'>"}
        oid = self._object_id(value)
        if oid not in heap:
            heap[oid] = None  # placeholder: reserved, encoded later by _drain
            queue.append(value)
        return {"t": "ref", "id": oid}

    def _drain(self, heap, queue) -> bool:
        truncated = False
        encoded = 0
        while queue:
            value = queue.popleft()
            oid = self.obj_ids[id(value)]
            if encoded >= MAX_HEAP_OBJECTS:
                heap[oid] = {"t": "other", "repr": "…（对象过多，已省略）"}
                truncated = True
                continue
            heap[oid] = self._encode_object(value, heap, queue)
            encoded += 1
        return truncated

    def _encode_object(self, value, heap, queue) -> dict:
        def enc(v):
            return self._encode(v, heap, queue)

        if is_link(value):
            rest = value.rest
            return {
                "t": "link",
                "first": enc(value.first),
                "rest": {"t": "empty"} if _is_link_empty(value, rest) else enc(rest),
            }
        if is_tree(value):
            return {
                "t": "tree",
                "label": enc(value.label),
                "branches": [enc(b) for b in value.branches[:MAX_ITEMS]],
            }
        if isinstance(value, (list, tuple, set, frozenset)):
            kind = {list: "list", tuple: "tuple"}.get(type(value), "set")
            items = list(value)
            return {
                "t": kind,
                "items": [enc(v) for v in items[:MAX_ITEMS]],
                "len": len(items),
            }
        if isinstance(value, dict):
            pairs = list(value.items())
            return {
                "t": "dict",
                "items": [[enc(k), enc(v)] for k, v in pairs[:MAX_ITEMS]],
                "len": len(pairs),
            }
        if isinstance(value, types.FunctionType):
            parent = self._register_function(value)
            is_lambda = value.__name__ == "<lambda>"
            try:
                params = str(inspect.signature(value))
            except (TypeError, ValueError):
                params = "(...)"
            return {
                "t": "func",
                "name": "λ" if is_lambda else value.__name__,
                "params": _truncate(params, 60),
                "parent": parent,
                "line": value.__code__.co_firstlineno if is_lambda else None,
            }
        if isinstance(value, (types.BuiltinFunctionType, types.BuiltinMethodType)):
            return {"t": "func", "name": value.__name__, "params": "(...)", "builtin": True}
        if isinstance(value, types.MethodType):
            return {
                "t": "method",
                "func": enc(value.__func__),
                "self": enc(value.__self__),
            }
        if isinstance(value, type):
            skip = {"__module__", "__qualname__", "__dict__", "__weakref__", "__doc__",
                    "__firstlineno__", "__static_attributes__"}
            attrs = [
                [k, enc(v)]
                for k, v in vars(value).items()
                if k not in skip
            ]
            bases = [b.__name__ for b in value.__bases__ if b is not object]
            return {"t": "class", "name": value.__name__, "bases": bases, "attrs": attrs}
        attrs = getattr(value, "__dict__", None)
        if isinstance(attrs, dict):
            return {
                "t": "instance",
                "cls": type(value).__name__,
                "attrs": [[k, enc(v)] for k, v in list(attrs.items())[:MAX_ITEMS]],
            }
        try:
            text = repr(value)
        except Exception:  # noqa: BLE001 - student objects can do anything
            text = f"<{type(value).__name__}>"
        return {"t": "other", "repr": _truncate(text)}

    # -------------------------------------------------------------- driver

    def run(self, code: str, globals_dict: dict) -> dict:
        linecache.cache[STUDENT_FILE] = (len(code), None, code.splitlines(True), STUDENT_FILE)
        try:
            compiled = compile(code, STUDENT_FILE, "exec")
        except SyntaxError as e:
            return {
                "ok": False,
                "steps": [],
                "calls": [],
                "error": {
                    "type": "SyntaxError",
                    "message": e.msg,
                    "line": e.lineno,
                    "traceback": "".join(traceback.format_exception_only(type(e), e)),
                },
            }
        self.module_code = compiled
        self.globals = globals_dict
        self._index_code(compiled)

        error = None
        old_stdout = sys.stdout
        old_limit = sys.getrecursionlimit()
        sys.stdout = self.stdout
        sys.setrecursionlimit(max(old_limit, 4000))
        sys.settrace(self.trace)
        try:
            exec(compiled, globals_dict)
        except StopTracing:
            pass
        except BaseException as e:  # noqa: BLE001 - report every student error
            error = _describe_exception(e)
            if self.steps:
                self.steps[-1]["exception"] = f"{error['type']}: {error['message']}"
                self.steps[-1]["uncaught"] = True
        finally:
            sys.settrace(None)
            sys.stdout = old_stdout
            sys.setrecursionlimit(old_limit)

        return {
            "ok": error is None and not self.truncated,
            "steps": self.steps,
            "calls": self.calls,
            "error": error,
            "truncated": self.truncated,
            "max_steps": self.max_steps,
            "stdout": self.stdout.getvalue()[-MAX_STDOUT:],
        }


def _describe_exception(exc: BaseException) -> dict:
    tb = exc.__traceback__
    line = None
    while tb is not None:
        if tb.tb_frame.f_code.co_filename == STUDENT_FILE:
            line = tb.tb_lineno
        tb = tb.tb_next
    frames = [
        fs
        for fs in traceback.extract_tb(exc.__traceback__)
        if fs.filename == STUDENT_FILE
    ]
    if len(frames) > 12:
        frames = frames[:5] + frames[-5:]
    text = "Traceback (most recent call last):\n"
    text += "".join(traceback.format_list(frames))
    text += "".join(traceback.format_exception_only(type(exc), exc))
    return {
        "type": type(exc).__name__,
        "message": str(exc),
        "line": line,
        "traceback": text,
    }


def trace_code(code: str, max_steps: int = MAX_STEPS_DEFAULT, builtins_dict: dict | None = None) -> dict:
    globals_dict = {"__name__": "__main__"}
    if builtins_dict is not None:
        globals_dict["__builtins__"] = builtins_dict
    return Tracer(max_steps=max_steps).run(code, globals_dict)
