from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def create_demo_data(session: AsyncSession):
    """Создает тестовых пользователей для демонстрации."""

    demo_users = [
        User(
            name="Демо-администратор",
            api_key="demo_admin_key",
            is_demo=True
        ),
        User(
            name="Демо-пользователь",
            api_key="demo_user_key",
            is_demo=True
        ),
        User(
            name="Тестовый сотрудник",
            api_key="employee_test_key",
            is_demo=False
        )
    ]

    session.add_all(demo_users)
    await session.commit()
