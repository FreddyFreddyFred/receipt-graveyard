"""Employee identity and optional expense context metadata."""

from pydantic import BaseModel


class Employee(BaseModel):
    """An employee identified by the receipt sidecar manifest."""

    employee_id: str
    name: str | None = None
    department: str | None = None
    trip_id: str | None = None
    city: str | None = None
