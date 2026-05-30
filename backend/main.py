from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import upload, analyze
from loguru import logger
from pathlib import Path

LOG_DIR = Path(__file__).resolve().parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
logger.add(str(LOG_DIR / "app_{time:YYYY-MM-DD}.log"), level="INFO",
           rotation="00:00", retention="30 days", encoding="utf-8",
           format="{time:YYYY-MM-DD HH:mm:ss} | {level:<7} | {message}")

app = FastAPI(title="KISIA ISMS-P 증적 점검 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(analyze.router)


@app.get("/health")
def health():
    return {"status": "ok"}
