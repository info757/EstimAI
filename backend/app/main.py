from dotenv import load_dotenv
load_dotenv()  # loads .env from project root

from fastapi import FastAPI
from .api.routes import r
app = FastAPI(title="EstimAI")
app.include_router(r, prefix="/api")
