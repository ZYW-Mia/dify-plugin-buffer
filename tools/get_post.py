from dify_plugin import Tool

from common.inputs import required_string
from common.queries import POST
from common.tool import invoke


class GetPostTool(Tool):
    def _invoke(self, tool_parameters):
        def operation(params):
            def execute(client, prepared):
                post = client.execute(POST, {"input": prepared})["post"]
                return {"post": post, "post_id": post["id"], "status": post["status"]}

            return {"id": required_string(params, "post_id")}, execute

        yield from invoke(self, tool_parameters, operation)
