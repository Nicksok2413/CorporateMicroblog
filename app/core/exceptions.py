"""Модуль кастомных исключений и их обработчиков для FastAPI.

Содержит специализированные исключения для разных сценариев
и функции для их корректной обработки и преобразования в HTTP-ответы.
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.core.logging import log
from app.schemas.base import ResultFalseWithError  # Импортируем базовую схему ошибки


class MicroblogHTTPException(HTTPException):
    """Базовое исключение для API микросервиса."""

    def __init__(
            self,
            status_code: int,
            detail: str,
            error_type: Optional[str] = None,
            headers: Optional[dict[str, Any]] = None,
            extra: Optional[dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.error_type = error_type or "microblog_error"
        self.extra = extra or {}


class NotFoundError(MicroblogHTTPException):
    """Ошибка при отсутствии запрашиваемого ресурса."""

    def __init__(self, detail: str = "Ресурс не найден", **kwargs):
        super().__init__(status.HTTP_404_NOT_FOUND, detail, "not_found", **kwargs)


class AuthenticationRequiredError(MicroblogHTTPException):
    """Ошибка при отсутствии заголовка `api-key`."""

    def __init__(self, detail: str = "Требуется аутентификация", headers: Optional[dict[str, Any]] = None, **kwargs):
        super().__init__(status.HTTP_401_UNAUTHORIZED, detail, "unauthorized", headers=headers, **kwargs)


class PermissionDeniedError(MicroblogHTTPException):
    """Ошибка доступа при отсутствии прав."""

    def __init__(self, detail: str = "Доступ запрещен", **kwargs):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "permission_denied", **kwargs)


class BadRequestError(MicroblogHTTPException):
    """Ошибка при невалидных входных данных."""

    def __init__(self, detail: str = "Некорректный запрос", **kwargs):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, "bad_request", **kwargs)


class ConflictError(MicroblogHTTPException):
    """Ошибка при конфликте данных (например, дубликат)."""

    def __init__(self, detail: str = "Конфликт данных", **kwargs):
        super().__init__(status.HTTP_409_CONFLICT, detail, "conflict_error", **kwargs)


class TweetValidationError(BadRequestError):
    """Ошибка валидации твита."""

    def __init__(self, detail: str = "Ошибка валидации твита", **kwargs):
        super().__init__(detail, "tweet_validation_error", **kwargs)


class MediaValidationError(BadRequestError):
    """Ошибка валидации медиафайла."""

    def __init__(self, detail: str = "Ошибка валидации медиа", **kwargs):
        super().__init__(detail, "media_validation_error", **kwargs)


class UserNotFoundError(NotFoundError):
    """Ошибка при отсутствии пользователя."""

    def __init__(self, api_key: Optional[str] = None):
        detail = "Пользователь не найден"
        extra = {"api_key": api_key} if api_key else {}
        super().__init__(detail=detail, extra=extra)


# --- Обработчики исключений FastAPI ---

async def microblog_exception_handler(request: Request, exc: MicroblogHTTPException) -> JSONResponse:
    """
    Обработчик для кастомных исключений MicroblogHTTPException.

    Формирует стандартный ответ ошибки, используя атрибуты исключения.

    Args:
        request: Объект запроса FastAPI.
        exc: Экземпляр MicroblogHTTPException или его наследника.

    Returns:
        JSONResponse: Ответ с ошибкой в стандартном формате.
    """
    log.bind(extra_info=exc.extra).warning(
        f"Обработана ошибка API ({exc.status_code} {exc.error_type}): {exc.detail}"
    )
    content = ResultFalseWithError(
        error_type=exc.error_type,
        error_message=exc.detail,
        extra_info=exc.extra
    ).model_dump()

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
        headers=getattr(exc, 'headers', None)  # Извлекаем headers из исключения
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """
    Обработчик ошибок валидации Pydantic (RequestValidationError).

    Форматирует ошибки валидации в читаемый вид и возвращает стандартный ответ.

    Args:
        request: Объект запроса FastAPI.
        exc: Экземпляр RequestValidationError.

    Returns:
        JSONResponse: Ответ с ошибкой валидации в стандартном формате.
    """
    error_messages = []
    for error in exc.errors():
        field = " -> ".join(map(str, error.get("loc", ["unknown"])))
        message = error.get("msg", "Unknown validation error")
        error_messages.append(f"Поле '{field}': {message}")

    error_detail = ". ".join(error_messages)
    log.warning(f"Ошибка валидации запроса: {error_detail}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResultFalseWithError(
            error_type="Validation Error",
            error_message=error_detail,
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик для всех остальных (непредвиденных) исключений.

    Логирует ошибку с трейсбэком и возвращает стандартизированный ответ 500 Internal Server Error.

    Args:
        request: Объект запроса FastAPI.
        exc: Экземпляр непредвиденного исключения.

    Returns:
        JSONResponse: Ответ 500 Internal Server Error в стандартном формате.
    """
    # Используем log.exception для автоматического добавления трейсбэка
    log.exception(f"Необработанное исключение во время запроса {request.method} {request.url.path}: {exc}")

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ResultFalseWithError(
            error_type="Internal Server Error",
            error_message="Произошла непредвиденная внутренняя ошибка сервера.",
        ).model_dump(),
    )


def setup_exception_handlers(app: FastAPI):
    """
    Регистрирует обработчики исключений в приложении FastAPI.

    Args:
        app: Экземпляр приложения FastAPI.
    """
    # Обработчик для наших кастомных ошибок (MicroblogHTTPException и наследники)
    app.add_exception_handler(MicroblogHTTPException, microblog_exception_handler)
    # Обработчик для ошибок валидации Pydantic
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    # Обработчик для всех остальных непредвиденных исключений
    app.add_exception_handler(Exception, generic_exception_handler)
    log.info("Обработчики исключений настроены.")
