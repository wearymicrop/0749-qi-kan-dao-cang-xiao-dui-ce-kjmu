from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StrictInt, StringConstraints

from app.modules.m1_orders.models import Key

NoteId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=40)]
Statement = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class PublicationNote(BaseModel):
    model_config = ConfigDict(extra="forbid")
    note_id: NoteId
    chain: Key
    title: Key
    span: Annotated[list[StrictInt], Field(min_length=2, max_length=2)]
    statement: Statement
