"""Describe a graph's state in plain words: which fields are overwritten and which appended."""

from typing import Annotated, get_args, get_origin, get_type_hints


def describe_fields(state_schema: type) -> dict[str, str]:
    """For each state field: "overwrite", or "append (<reducer>)" when a reducer is attached."""
    fields = {}
    for name, hint in get_type_hints(state_schema, include_extras=True).items():
        if get_origin(hint) is Annotated:
            reducer = get_args(hint)[1]
            # LangGraph wraps add_messages in a helper called "_add_messages"
            reducer_name = getattr(reducer, "__name__", repr(reducer)).lstrip("_")
            fields[name] = f"append ({reducer_name})"
        else:
            fields[name] = "overwrite"
    return fields
