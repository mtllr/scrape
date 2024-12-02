from typing import Generic, TypeVar, Optional
from pydantic import BaseModel, Field
from datetime import datetime

DataT = TypeVar("DataT")


class ScrapeModel(BaseModel, Generic[DataT]):
    script: str = Field(..., description="The name of the script in python module form")
    script_version: str = Field(..., description="The version of the script")
    args: list[str] = Field(
        ...,
        description="The list of arguments used to call the script. To make script calls uniquely identifiable",
    )
    url: str = Field(
        ...,
        description="The scraped url",
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.now().isoformat(timespec="seconds"),
        description="The timestamp when the data was scraped",
    )
    data: Optional[DataT] = Field(None, description="The scraped contents")
