"""Heimdall systems monitoring suite"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import run

from heimdall import cfg
from heimdall.db import database, init_database
from heimdall.monitor import Monitor, MonitorModel


app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["HEAD", "GET"], allow_headers=["*"])
monitor = Monitor()
monitor.load_from_config(cfg.CONFIG_FILE)


@app.on_event("startup")
async def startup():
    await database.connect()
    init_database()
    monitor.start()


@app.on_event("shutdown")
async def shutdown():
    await monitor.stop()
    await database.disconnect()


@app.get("/", response_model=MonitorModel)
async def root():
    return monitor.as_model()


if __name__ == "__main__":
    run(
        "main:app",
        host=cfg.HOST,
        port=cfg.PORT,
        reload=cfg.DEBUG,
        access_log=cfg.DEBUG,
        log_config=cfg.LOG_CONFIG,
        proxy_headers=True,
        forwarded_allow_ips=cfg.FORWARDED_ALLOWED_IPS,
    )
