import ast
import inspect
from pathlib import Path

import pytest
import server


def test_list_servers_has_exactly_one_mcp_tool_decorator():
    server_file = inspect.getsourcefile(server)
    assert server_file is not None, "Unable to resolve server.py location from imported server module"
    server_path = Path(server_file)
    assert server_path.exists(), f"Resolved server.py path does not exist: {server_path}"
    try:
        module = ast.parse(server_path.read_text(encoding="utf-8"))
    except SyntaxError as exc:
        pytest.fail(f"Unable to parse {server_path}: {exc}")

    list_servers = None
    for node in module.body:
        if isinstance(node, ast.FunctionDef) and node.name == "list_servers":
            list_servers = node
            break
    assert list_servers is not None, "list_servers function not found in server.py"

    mcp_tool_decorators = []
    for decorator in list_servers.decorator_list:
        if (
            isinstance(decorator, ast.Call)
            and isinstance(decorator.func, ast.Attribute)
            and isinstance(decorator.func.value, ast.Name)
            and decorator.func.value.id == "mcp"
            and decorator.func.attr == "tool"
        ):
            mcp_tool_decorators.append(decorator)
        elif (
            isinstance(decorator, ast.Attribute)
            and isinstance(decorator.value, ast.Name)
            and decorator.value.id == "mcp"
            and decorator.attr == "tool"
        ):
            mcp_tool_decorators.append(decorator)

    assert len(mcp_tool_decorators) == 1, (
        f"Expected exactly 1 @mcp.tool or @mcp.tool() decorator on list_servers, "
        f"but found {len(mcp_tool_decorators)}"
    )
