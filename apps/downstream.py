import os
import time
from fastapi import FastAPI, HTTPException
from common import configure

app = FastAPI(title="SRE Downstream")
configure(app, "downstream")


@app.get("/process")
def process():
    delay = min(max(float(os.getenv("PROCESS_DELAY_SECONDS", "0")), 0.0), 4.0)
    if delay:
        time.sleep(delay)
    if os.getenv("FORCE_FAILURE", "false").lower() == "true":
        raise HTTPException(status_code=503, detail="injected dependency failure")
    return {"processed": True}
