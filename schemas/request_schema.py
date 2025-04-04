

# schemas/request_schema.py
from pydantic import BaseModel
from datetime import date

class PanchangRequest(BaseModel):
    date: date
    location: str