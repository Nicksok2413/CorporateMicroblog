"""Модуль кастомных исключений и их обработчиков для FastAPI.

Содержит специализированные исключения для разных сценариев
и функции для их корректной обработки и преобразования в HTTP-ответы.
"""

from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Импортируем логгер
from app.core.logging import log

# Импортируем базовую схему ошибки
try:
    # Предполагаем, что схема находится здесь
    from app.schemas.base import ResultFalseWithError
except ImportError:
    log.warning("Не удалось импортировать ResultFalseWithError из app.schemas.base. Используется заглушка.")


    # Заглушка, если схема еще не создана или находится в другом месте
    class ResultFalseWithError:
        def __init__(self, result: bool = False, error_type: str = "Error", error_message: Any = "Unknown error",
                     **kwargs):
            self.result = result
            self.error_type = error_type
            self.error_message = error_message
            # Сохраняем доп. поля, если они переданы
            self.extra_info = kwargs.get("extra_info")

        def model_dump(self) -> Dict[str, Any]:
            data = {
                "result": self.result,
                "error_type": self.error_type,
                "error_message": self.error_message,
            }
            if self.extra_info:
                data["extra_info"] = self.extra_info
            return data


# --- Ваши классы исключений (оставляем без изменений) ---

class MicroblogHTTPException(HTTPException):
    """Базовое исключение для API микросервиса."""

    def __init__(
            self,
            status_code: int,
            detail: str,
            error_type: Optional[str] = None,
            extra: Optional[dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_type = error_type or "microblog_error"
        self.extra = extra or {}


class NotFoundError(MicroblogHTTPException):
    """Ошибка при отсутствии запрашиваемого ресурса."""

    def __init__(self, detail: str = "Ресурс не найден", **kwargs):
        super().__init__(status.HTTP_404_NOT_FOUND, detail, "not_found", **kwargs)


class PermissionDeniedError(MicroblogHTTPException):
    """Ошибка доступа при отсутствии прав."""

    def __init__(self, detail: str = "Доступ запрещен", **kwargs):
        super().__init__(status.HTTP_403_FORBIDDEN, detail, "permission_denied", **kwargs)


class BadRequestError(MicroblogHTTPException):
    """Ошибка при невалидных входных данных."""

    def __init__(self, detail: str = "Некорректный запрос", **kwargs):
        super().__init__(status.HTTP_400_BAD_REQUEST, detail, "bad_request", **kwargs)


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
        extra_info=exc.extra  # Передаем extra в схему
    ).model_dump()

    return JSONResponse(
        status_code=exc.status_code,
        content=content,
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
    log.warning(f"Ошибка валидации запроса: {error_detail}")  # Логгируем ошибку валидации
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=ResultFalseWithError(
            error_type="Validation Error",
            error_message=error_detail,
            # Можно передать exc.errors() в extra_info, если нужно на клиенте
            # extra_info={"validation_errors": exc.errors()}
        ).model_dump(),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    Обработчик для всех остальных (непредвиденных) исключений.

    Логгирует ошибку с трейсбэком и возвращает стандартизированный ответ 500 Internal Server Error.

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
    # Обработчик для стандартного HTTPException (если он где-то используется напрямую)
    # Убедитесь, что он не конфликтует с MicroblogHTTPException, если тот наследуется от него
    # app.add_exception_handler(HTTPException, http_exception_handler) # Возможно, не нужен, если все ошибки через MicroblogHTTPException
    # Обработчик для всех остальных непредвиденных исключений (всегда последний)
    app.add_exception_handler(Exception, generic_exception_handler)
    log.info("Обработчики исключений настроены.")
