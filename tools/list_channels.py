from dify_plugin import Tool

from common.inputs import required_string
from common.queries import CHANNELS
from common.tool import invoke


class ListChannelsTool(Tool):
    def _invoke(self, tool_parameters):
        def operation(params):
            prepared = {"organizationId": required_string(params, "organization_id")}

            def execute(client, prepared):
                channels = client.execute(CHANNELS, {"input": prepared})["channels"]
                return {"channels": channels, "count": len(channels)}

            return prepared, execute

        yield from invoke(self, tool_parameters, operation)
