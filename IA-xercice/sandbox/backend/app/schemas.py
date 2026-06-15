from datetime import datetime

from pydantic import BaseModel, Field


class GuestbookEntryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    message: str = Field(min_length=1, max_length=2000)


class GuestbookEntryRead(BaseModel):
    id: int
    name: str
    message: str
    created_at: datetime

    model_config = {"from_attributes": True}
