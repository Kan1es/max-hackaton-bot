from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    database: str
    version: str = "0.1.0"
