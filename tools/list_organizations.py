from dify_plugin import Tool

from common.queries import ORGANIZATIONS
from common.tool import invoke


class ListOrganizationsTool(Tool):
    def _invoke(self, tool_parameters):
        def operation(params):
            def execute(client, prepared):
                organizations = client.execute(ORGANIZATIONS)["account"]["organizations"]
                return {"organizations": organizations, "count": len(organizations)}

            return {}, execute

        yield from invoke(self, tool_parameters, operation)
