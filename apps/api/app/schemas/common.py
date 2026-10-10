from pydantic import BaseModel, ConfigDict


class ApiModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class RequestModel(BaseModel):
    """Inbound bodies reject unknown fields, so e.g. a client-sent "amount" is an error."""

    model_config = ConfigDict(extra="forbid")


class Page[T](ApiModel):
    items: list[T]
    total: int
    limit: int
    offset: int
