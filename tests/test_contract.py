from pathlib import Path

import pytest
from graphql import build_schema, parse, validate
from graphql.utilities import coerce_input_value

from common import queries
from common.inputs import post_input

SCHEMA = build_schema(Path("tests/fixtures/buffer_contract.graphql").read_text())


@pytest.mark.parametrize(
    "name",
    [
        "ACCOUNT",
        "ORGANIZATIONS",
        "CHANNELS",
        "POSTS",
        "POST",
        "CREATE_POST",
        "EDIT_POST",
        "DELETE_POST",
    ],
)
def test_operations_match_published_buffer_contract(name):
    errors = validate(SCHEMA, parse(getattr(queries, name)))
    assert not errors, [error.message for error in errors]


@pytest.mark.parametrize(
    "params,editing",
    [
        ({"channel_id": "c", "text": "Hello"}, False),
        (
            {
                "channel_id": "c",
                "assets_json": '[{"image":{"url":"https://example.com/x.png"}}]',
                "metadata_json": '{"instagram":{"type":"post","shouldShareToFeed":true}}',
            },
            False,
        ),
        ({"post_id": "p", "text": "Edited"}, True),
        ({"post_id": "p", "mode": "customScheduled", "due_at": "2099-01-01T00:00:00Z"}, True),
    ],
)
def test_generated_post_inputs_match_buffer_types(params, editing):
    value = post_input(params, editing=editing)
    name = "EditPostInput" if editing else "CreatePostInput"
    assert coerce_input_value(value, SCHEMA.get_type(name))
