

from fastapi import FastAPI, HTTPException
from datetime import datetime
from models.panchang import Panchang
from schemas.request_schema import PanchangRequest
from services.llm_service import generate_panchang

app = FastAPI()

@app.post("/panchang", response_model=Panchang)
async def get_panchang(request: PanchangRequest):
    try:
        return generate_panchang(request.date, request.location)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
