from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from common.client import BufferClient, BufferError


def messages(tool: Tool, result: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
    yield tool.create_json_message(result)
    for name, value in result.items():
        if value is not None:
            yield tool.create_variable_message(name, value)


def invoke(tool: Tool, params: dict, operation):
    try:
        # Validate parameters before opening the connection or performing any write.
        prepared, execute = operation(params)
        with BufferClient(tool.runtime.credentials) as client:
            result = execute(client, prepared)
        yield from messages(tool, result)
    except (BufferError, ValueError) as exc:
        raise RuntimeError(str(exc)) from exc
