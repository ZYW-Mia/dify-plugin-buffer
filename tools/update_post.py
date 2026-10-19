from dify_plugin import Tool

from common.inputs import post_input
from common.queries import EDIT_POST
from common.tool import invoke


class UpdatePostTool(Tool):
    def _invoke(self, tool_parameters):
        def operation(params):
            def execute(client, prepared):
                post = client.mutation(EDIT_POST, "editPost", prepared, "PostActionSuccess")["post"]
                return {"post": post, "post_id": post["id"], "status": post["status"]}

            return post_input(params, editing=True), execute

        yield from invoke(self, tool_parameters, operation)
