from logging import INFO, ERROR

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.starlette import StarletteIntegration

from src.core.config import settings
from src.core.logging import log


def initialize_sentry():
    """
    Инициализирует Sentry SDK, если задан DSN.
    Определяет environment, sample rates и другие параметры на основе settings.
    """
    sentry_dsn = settings.SENTRY_DSN

    if not sentry_dsn:
        log.warning("SENTRY_DSN не установлен в .env. Sentry SDK не инициализирован.")
        return

    # --- Определяем параметры Sentry ---

    # 1. Окружение (Environment)
    if settings.PRODUCTION:
        environment = "production"
    elif settings.TESTING:
        environment = "testing"
    else:  # Development (DEBUG=True)
        environment = "development"

    # 2. Частота семплирования для Performance Monitoring (Traces)
    # Установим 10% для production, 100% для development, 0% для testing
    if environment == "production":
        traces_sample_rate = 0.1
    elif environment == "development":
        traces_sample_rate = 1.0  # Отслеживаем все в разработке
    else:  # testing
        traces_sample_rate = 0.0  # Не отправляем трейсы из тестов

    # 3. Частота семплирования для Profiling
    # Аналогично трейсам, или можно задать другие значения
    if environment == "production":
        profiles_sample_rate = 0.1
    elif environment == "development":
        profiles_sample_rate = 1.0
    else:  # testing
        profiles_sample_rate = 0.0

    # 4. Уровни логирования для интеграции
    log_level_breadcrumbs = INFO  # Уровень для breadcrumbs
    log_level_events = ERROR  # Уровень для событий/ошибок

    log.info(
        f"Инициализация Sentry SDK. DSN: {'***' + sentry_dsn[-6:]}, "
        f"Environment: {environment}, "
        f"Traces Rate: {traces_sample_rate}, "
        f"Profiles Rate: {profiles_sample_rate}"
    )

    try:
        sentry_sdk.init(
            dsn=sentry_dsn,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(transaction_style="endpoint"),
                SqlalchemyIntegration(),
                LoggingIntegration(
                    level=log_level_breadcrumbs, event_level=log_level_events
                ),
            ],
            environment=environment,
            traces_sample_rate=traces_sample_rate,
            profiles_sample_rate=profiles_sample_rate,
            release=f"microblog@{settings.API_VERSION}",
        )
        log.success("Sentry SDK успешно инициализирован.")
    except Exception as exc:
        log.exception(f"Ошибка инициализации Sentry SDK: {exc}")
