from dify_plugin import Tool

from common.inputs import POST_STATUSES, page_size, required_string, string_list, utc_time
from common.queries import POSTS
from common.tool import invoke


class ListPostsTool(Tool):
    def _invoke(self, tool_parameters):
        def operation(params):
            filters = {}
            if params.get("channel_ids_json") not in (None, ""):
                filters["channelIds"] = string_list(params["channel_ids_json"], "channel_ids_json")
            if params.get("status") and params["status"] != "all":
                if params["status"] not in POST_STATUSES:
                    raise ValueError("Invalid post status filter.")
                filters["status"] = [params["status"]]
            for param, field in (("start_date", "startDate"), ("end_date", "endDate")):
                if params.get(param):
                    filters[field] = utc_time(params[param], param)
            if filters.get("startDate") and filters.get("endDate"):
                if filters["startDate"] > filters["endDate"]:
                    raise ValueError("start_date must be before end_date.")
            input_data = {"organizationId": required_string(params, "organization_id")}
            if filters:
                input_data["filter"] = filters
            prepared = {"input": input_data, "first": page_size(params.get("first"))}
            if params.get("after"):
                prepared["after"] = required_string(params, "after")

            def execute(client, prepared):
                result = client.execute(POSTS, prepared)["posts"]
                posts = [edge["node"] for edge in result.get("edges") or [] if edge]
                page = result["pageInfo"]
                return {
                    "posts": posts,
                    "count": len(posts),
                    "has_next_page": page["hasNextPage"],
                    "end_cursor": page.get("endCursor") or "",
                }

            return prepared, execute

        yield from invoke(self, tool_parameters, operation)
