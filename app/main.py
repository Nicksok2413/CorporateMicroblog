from contextlib import asynccontextmanager

from fastapi import FastAPI, Request

from app.core.logging import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("Starting application...")
    try:
        yield
    except Exception as e:
        log.error(f"Application error: {e}")
        raise
    finally:
        log.info("Application shutdown")


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    log.info(f"Request: {request.method} {request.url}")
    response = await call_next(request)
    log.info(f"Response: {response.status_code}")
    return response
