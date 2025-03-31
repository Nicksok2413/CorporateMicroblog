from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.core.exceptions import MicroblogHTTPException
from app.core.logging import log


@asynccontextmanager
async def lifespan(app: FastAPI):
    # # Подключение к БД
    # await db.connect()
    #
    # # Создание демо-данных в dev-режиме
    # if settings.DEBUG and not settings.TESTING:
    #     async with db.session() as session:
    #         await create_demo_data(session)
    #
    # yield
    #
    # # Завершение работы
    # await db.disconnect()

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


@app.exception_handler(MicroblogHTTPException)
async def microblog_exception_handler(
        request: Request, exc: MicroblogHTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "result": False,
            "error_type": exc.error_type,
            "error_message": exc.detail,
            **exc.extra
        }
    )
