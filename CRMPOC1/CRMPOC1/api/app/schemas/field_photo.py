from datetime import datetime

from pydantic import BaseModel


class FieldPhotoOut(BaseModel):
    id: int
    source: str
    serial_no: str | None = None
    file_path: str
    latitude: float
    longitude: float
    accuracy_m: float | None = None
    captured_at: datetime | None = None
    created_at: datetime | None = None
    uploaded_by_name: str | None = None
    map_url: str
