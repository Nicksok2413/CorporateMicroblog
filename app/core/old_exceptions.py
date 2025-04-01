"""Модуль кастомных исключений для микросервиса блогов.

Содержит специализированные исключения для разных сценариев:
- Ошибки аутентификации
- Ошибки работы с контентом
- Ошибки валидации
"""

from typing import Any, Optional

from fastapi import HTTPException, status


class MicroblogHTTPException(HTTPException):
    """Базовое исключение для API микросервиса.

    Args:
        status_code: HTTP статус-код
        detail: Детальное описание ошибки
        error_type: Тип ошибки для клиента
        extra: Дополнительные данные об ошибке
    """

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
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=detail,
            error_type="not_found",
            **kwargs
        )


class PermissionDeniedError(MicroblogHTTPException):
    """Ошибка доступа при отсутствии прав."""

    def __init__(self, detail: str = "Доступ запрещен", **kwargs):
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
            error_type="permission_denied",
            **kwargs
        )


class BadRequestError(MicroblogHTTPException):
    """Ошибка при невалидных входных данных."""

    def __init__(self, detail: str = "Некорректный запрос", **kwargs):
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=detail,
            error_type="bad_request",
            **kwargs
        )


class TweetValidationError(BadRequestError):
    """Ошибка валидации твита."""

    def __init__(self, detail: str = "Ошибка валидации твита", **kwargs):
        super().__init__(
            detail=detail,
            error_type="tweet_validation_error",
            **kwargs
        )


class MediaValidationError(BadRequestError):
    """Ошибка валидации медиафайла."""

    def __init__(self, detail: str = "Ошибка валидации медиа", **kwargs):
        super().__init__(
            detail=detail,
            error_type="media_validation_error",
            **kwargs
        )


class UserNotFoundError(NotFoundError):
    """Ошибка при отсутствии пользователя."""

    def __init__(self, api_key: Optional[str] = None):
        detail = "Пользователь не найден"
        extra = {}
        if api_key:
            extra["api_key"] = api_key
        super().__init__(detail=detail, extra=extra)
