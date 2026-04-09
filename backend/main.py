from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from temporalio.client import Client
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from typing import Optional
from pydantic import BaseModel
import os
from dotenv import set_key
import time

import database, models, schemas, temporal_utils
from temporal.workflows import NewsProductionWorkflow, StopStreamWorkflow


# ================= LIFESPAN ================= #

@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()

    db_gen = database.get_db()
    db = next(db_gen)

    try:
        if not db.query(models.User).filter(models.User.id == 1).first():
            default_user = models.User(
                id=1,
                email="admin@vartapravah.com",
                hashed_password="hashed_password",
                full_name="Admin User"
            )
            db.add(default_user)
            db.commit()
    finally:
        db.close()

    yield


app = FastAPI(title="VartaPravah API", lifespan=lifespan)


# ================= CORS ================= #

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ================= ROOT ================= #

@app.get("/")
def read_root():
    return {"status": "VartaPravah API Engine Online", "version": "1.0.0"}


# ================= TEMPORAL ================= #

async def get_temporal_client():
    try:
        return await temporal_utils.get_temporal_client()
    except Exception:
        raise HTTPException(status_code=500, detail="Temporal connection failed")


# ================= SETTINGS ================= #

class SettingsUpdate(BaseModel):
    groq_api_key: Optional[str] = None