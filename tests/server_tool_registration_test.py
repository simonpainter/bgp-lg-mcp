import ast
from pathlib import Path


def test_list_servers_has_single_mcp_tool_decorator():
    server_path = Path(__file__).resolve().parents[1] / "server.py"
    module = ast.parse(server_path.read_text())

    list_servers = next(
        (node for node in module.body if isinstance(node, ast.FunctionDef) and node.name == "list_servers"),
        None,
    )
    assert list_servers is not None, "list_servers function not found in server.py"

    mcp_tool_decorators = [
        decorator
        for decorator in list_servers.decorator_list
        if isinstance(decorator, ast.Call)
        and isinstance(decorator.func, ast.Attribute)
        and isinstance(decorator.func.value, ast.Name)
        and decorator.func.value.id == "mcp"
        and decorator.func.attr == "tool"
    ]

    assert len(mcp_tool_decorators) == 1, (
        f"Expected exactly 1 @mcp.tool() decorator on list_servers, "
        f"but found {len(mcp_tool_decorators)}"
    )
