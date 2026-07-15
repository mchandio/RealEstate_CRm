"""Data models: FieldSpec, ColumnSpec, TableSpec."""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable

@dataclass
class FieldSpec:
    label: str
    key: str
    kind: str = "entry"
    default: Any = ""
    options: list[str] = field(default_factory=list)
    required: bool = False
    numeric: bool = False


@dataclass
class ColumnSpec:
    key: str
    label: str
    formatter: Callable[[Any, str], str] | None = None
    width: int = 130


@dataclass
class TableSpec:
    title: str
    table: str
    columns: list[ColumnSpec]
    form_fields: list[FieldSpec]
    insert_columns: list[str]
    update_columns: list[str]
    permission: str = "rent"
    order_by: str = "id DESC"
    deal_table: bool = False


