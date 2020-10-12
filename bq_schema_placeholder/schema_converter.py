"""
Convert a bigquery schema into the source code for a data class.
"""
import itertools
import inspect
from typing import List

from google.cloud.bigquery import SchemaField

from .types import BigQueryFieldModes, BigQueryTypes, TypeMapping

_TEMPLATE_DATACLASS = """
@dataclass
class {schema_name}:
{fields}
"""
_TEMPLATE_FIELD = "    {field_name}: {field_type}"
_TEMPLATE_FIELD_WITH_DESCRIPTION = '    {field_name}: {field_type} = field(metadata={{"description": "{field_description}"}})'


def schema_to_dataclass(
    schema_name: str, schema: List[SchemaField], nested_schema: bool = False
) -> str:
    struct_fields = [s for s in schema if s.field_type == "STRUCT"]
    nested_dataclasses = "".join(
        schema_to_dataclass(s.name, s.fields, True) for s in struct_fields
    )
    dataclass_fields = [_create_field(field) for field in schema]
    python_dataclass = _TEMPLATE_DATACLASS.format(
        schema_name=_generate_dataclass_name(schema_name),
        fields="\n".join(dataclass_fields),
    ).strip()

    return (
        f"{python_dataclass}\n"
        if nested_schema
        else f"{nested_dataclasses}\n{python_dataclass}"
    )


def _create_field(field: SchemaField) -> str:
    bigquery_type = BigQueryTypes[field.field_type]
    if bigquery_type == BigQueryTypes.STRUCT:
        dataclass_type = _generate_dataclass_name(field.name)
    else:
        dataclass_type = TypeMapping[bigquery_type].__name__

    field_mode = BigQueryFieldModes[field.mode]

    if field_mode == BigQueryFieldModes.REPEATED:
        dataclass_type = f"List[{dataclass_type}]"
    if field_mode == BigQueryFieldModes.NULLABLE:
        dataclass_type = f"Optional[{dataclass_type}]"

    field_string = {
        "template": _TEMPLATE_FIELD,
        "args": {
            "field_name": field.name,
            "field_type": dataclass_type,
        },
    }

    if field.description:
        field_string["template"] = _TEMPLATE_FIELD_WITH_DESCRIPTION
        field_string["args"]["field_description"] = field.description

    return field_string["template"].format(**field_string["args"])


def _generate_dataclass_name(schema_name: str) -> str:
    return (
        "".join(word.capitalize() for word in schema_name.split("_"))
        if "_" in schema_name
        else schema_name
    )
