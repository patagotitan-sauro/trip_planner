"""Fail when float is used for money in apps/ and servicos/ (AGENTS.md section 11)."""

import ast
import re
import sys
from collections.abc import Iterator
from pathlib import Path

SCOPE = ("apps", "servicos")
MONEY_WORDS = {
    "amount", "price", "cost", "total", "budget", "balance", "fee", "expense", "rate",
    "valor", "preco", "custo", "orcamento", "saldo", "taxa", "despesa", "cambio",
}  # fmt: skip
ALLOW = re.compile(r"#\s*allow-float:\s*\S")

Node = ast.expr | ast.stmt | ast.arg
Violation = tuple[Node, str]


def is_money_name(name: str) -> bool:
    return any(
        part in MONEY_WORDS
        or part.removesuffix("s") in MONEY_WORDS
        or part.removesuffix("es") in MONEY_WORDS
        for part in name.lower().split("_")
    )


def name_of(node: ast.expr) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def has_float_value(node: ast.expr) -> bool:
    return any(
        (isinstance(n, ast.Constant) and isinstance(n.value, float))
        or (isinstance(n, ast.Call) and name_of(n.func) == "float")
        for n in ast.walk(node)
    )


def mentions_float_type(node: ast.expr) -> bool:
    return any(isinstance(n, ast.Name) and n.id == "float" for n in ast.walk(node))


def find_violations(tree: ast.AST) -> Iterator[Violation]:
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and name_of(node.func) == "FloatField":
            yield node, "FloatField is inexact; use DecimalField"
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                name = name_of(target)
                if name and is_money_name(name) and has_float_value(node.value):
                    yield node, f"'{name}' is assigned a float; use Decimal"
        elif isinstance(node, ast.AnnAssign):
            name = name_of(node.target)
            if name and is_money_name(name):
                if mentions_float_type(node.annotation):
                    yield node, f"'{name}' is annotated float; use Decimal"
                elif node.value and has_float_value(node.value):
                    yield node, f"'{name}' is assigned a float; use Decimal"
        elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            for arg in node.args.posonlyargs + node.args.args + node.args.kwonlyargs:
                if (
                    is_money_name(arg.arg)
                    and arg.annotation
                    and mentions_float_type(arg.annotation)
                ):
                    yield arg, f"parameter '{arg.arg}' is annotated float; use Decimal"
            if is_money_name(node.name) and node.returns and mentions_float_type(node.returns):
                yield node.returns, f"'{node.name}' returns float; use Decimal"


def check_file(path: Path) -> list[str]:
    source = path.read_text(encoding="utf-8")
    lines = source.splitlines()
    found = []
    for node, message in find_violations(ast.parse(source, filename=str(path))):
        if any(ALLOW.search(line) for line in lines[node.lineno - 1 : node.end_lineno]):
            continue
        found.append((node.lineno, node.col_offset, f"{path}:{node.lineno}: {message}"))
    return [text for _, _, text in sorted(found)]


def in_scope(path: Path) -> bool:
    return path.suffix == ".py" and path.parts[0] in SCOPE and "migrations" not in path.parts


def main(argv: list[str]) -> int:
    candidates = [Path(a) for a in argv] or [p for d in SCOPE for p in Path(d).rglob("*.py")]
    files = [p for p in candidates if in_scope(p)]
    problems = [line for path in files for line in check_file(path)]
    for line in problems:
        print(line)
    if problems:
        print(f"{len(problems)} float-for-money problem(s). Use Decimal (AGENTS.md section 11).")
        return 1
    print(f"No float-for-money found ({len(files)} files checked).")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
