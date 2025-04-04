


# panchang-api/models/panchang.py
from datetime import date
from pydantic import BaseModel

class Panchang(BaseModel):
    date: date
    sunrise: str
    sunset: str
    moonrise: str
    moonset: str
    tithi: str
    nakshatra: str
    yoga: str
    karana: str
    paksha: str
    day: str
    dishashool: str
    shaka_samvat: str
    vikram_samvat: str
    timings: dict