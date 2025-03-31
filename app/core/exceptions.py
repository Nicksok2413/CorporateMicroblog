class BaseServiceError(Exception):
    """Базовое исключение для всех ошибок в сервисах."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class NotFoundError(BaseServiceError):
    """Исключение, выбрасываемое, когда объект не найден."""
    def __init__(self, message: str = "Resource not found"):
        super().__init__(message)


class AlreadyExistsError(BaseServiceError):
    """Исключение, выбрасываемое, когда объект уже существует."""
    def __init__(self, message: str = "Resource already exists"):
        super().__init__(message)


class ValidationError(BaseServiceError):
    """Исключение для ошибок валидации."""
    def __init__(self, message: str = "Validation failed"):
        super().__init__(message)


class UnauthorizedError(BaseServiceError):
    """Исключение для неавторизованных запросов."""
    def __init__(self, message: str = "Unauthorized access"):
        super().__init__(message)


class ForbiddenError(BaseServiceError):
    """Исключение для запрещенных действий."""
    def __init__(self, message: str = "Forbidden"):
        super().__init__(message)


class ConflictError(BaseServiceError):
    """Исключение для конфликта данных."""
    def __init__(self, message: str = "Conflict error"):
        super().__init__(message)


class InternalServerError(BaseServiceError):
    """Исключение для внутренних ошибок сервера."""
    def __init__(self, message: str = "Internal server error"):
        super().__init__(message)
