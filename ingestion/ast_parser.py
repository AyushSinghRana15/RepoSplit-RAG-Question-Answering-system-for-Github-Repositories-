import ast
from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class ASTChunk:
    name: str
    kind: str
    start_line: int
    end_line: int
    calls: List[str] = field(default_factory=list)
    decorators: List[str] = field(default_factory=list)
    docstring: Optional[str] = None
    content: str = ""
    is_async: bool = False


def _extract_calls(node) -> List[str]:
    calls = []
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                calls.append(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                calls.append(child.func.attr)
    return list(set(calls))


def _get_docstring(node) -> Optional[str]:
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        doc = ast.get_docstring(node)
        if doc:
            return doc
    return None


def _get_decorators(node) -> List[str]:
    decorators = []
    if hasattr(node, 'decorator_list'):
        for d in node.decorator_list:
            if isinstance(d, ast.Name):
                decorators.append(d.id)
            elif isinstance(d, ast.Attribute):
                decorators.append(d.attr)
            elif isinstance(d, ast.Call):
                if isinstance(d.func, ast.Name):
                    decorators.append(d.func.id)
    return decorators


def parse_python_ast(source_code: str, file_path: str) -> List[dict]:
    try:
        tree = ast.parse(source_code)
    except SyntaxError:
        return []

    chunks = []
    lines = source_code.split('\n')
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            start = node.lineno
            end = node.end_lineno if hasattr(node, 'end_lineno') else start
            content = '\n'.join(lines[start-1:end])
            chunk = ASTChunk(
                name=node.name,
                kind='function',
                start_line=start,
                end_line=end,
                calls=_extract_calls(node),
                decorators=_get_decorators(node),
                docstring=_get_docstring(node),
                content=content,
                is_async=isinstance(node, ast.AsyncFunctionDef)
            )
            chunks.append(chunk)
        elif isinstance(node, ast.ClassDef):
            start = node.lineno
            end = node.end_lineno if hasattr(node, 'end_lineno') else start
            content = '\n'.join(lines[start-1:end])
            chunk = ASTChunk(
                name=node.name,
                kind='class',
                start_line=start,
                end_line=end,
                calls=_extract_calls(node),
                decorators=_get_decorators(node),
                docstring=_get_docstring(node),
                content=content
            )
            chunks.append(chunk)

    if not chunks:
        return []

    result = []
    for c in chunks:
        meta = {
            "file_path": file_path,
            "language": "python",
            "chunk_type": c.kind,
            "name": c.name,
            "start_line": c.start_line,
            "end_line": c.end_line,
            "char_count": len(c.content),
            "calls": c.calls,
            "decorators": c.decorators,
            "docstring": c.docstring,
            "is_async": c.is_async
        }
        result.append({"content": c.content, "metadata": meta})
    return result
