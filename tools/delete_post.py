from dify_plugin import Tool

from common.inputs import required_string
from common.queries import DELETE_POST
from common.tool import invoke


class DeletePostTool(Tool):
    def _invoke(self, tool_parameters):
        def operation(params):
            def execute(client, prepared):
                result = client.mutation(DELETE_POST, "deletePost", prepared, "DeletePostSuccess")
                return {"post_id": result["id"], "deleted": True}

            return {"id": required_string(params, "post_id")}, execute

        yield from invoke(self, tool_parameters, operation)
