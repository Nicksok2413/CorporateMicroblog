"""
Последовательно выполняет команды для обслуживания Git репозитория:
1. Создает резервную копию каталога .git
2. Переходит в .git/objects/
3. Удаляет пустые файлы в .git/objects/
4. Выполняет git fetch -p (загрузка изменений и удаление устаревших веток)
5. Выполняет git fsck --full (полная проверка целостности)
6. Возвращается в корневой каталог репозитория
7. Показывает git status
8. Удаляет резервную копию .git-old
9. Снова показывает git status

Требует наличия git, cp, find, rm в системном PATH.
Запускать из корневой директории Git репозитория.
"""

import subprocess
import sys
import os
# import shlex  # Хотя здесь не используется напрямую, полезен для разбора команд

# --- Конфигурация ---
GIT_DIR = ".git"
BACKUP_DIR = ".git-old"

# --- Команды для выполнения ---
COMMANDS = [
    f"cp -a {GIT_DIR} {BACKUP_DIR}",
    f"cd {GIT_DIR}/objects && find -type f -empty -delete && cd ../..",
    "git fetch -p",
    "git fsck --full",
    "git status",
    f"rm -rf {BACKUP_DIR}",
    # "git status"
]


# --- Функция для выполнения команды ---
def run_command(command_str):
    """Выполняет команду оболочки, выводит ее вывод и обрабатывает ошибки."""
    print("-" * 60)
    print(f"▶️ Выполнение: {command_str}")
    print("-" * 60)
    try:
        # shell=True необходим для команд, использующих '&&' или встроенные команды оболочки ('cd'),
        # чтобы они влияли на последующие команды в том же контексте выполнения.
        # check=True вызывает CalledProcessError при ненулевом коде возврата.
        # text=True (или encoding='utf-8') декодирует stdout/stderr как текст.
        # stderr=subprocess.STDOUT перенаправляет stderr в stdout для упрощения вывода.
        # Используем Popen для потокового вывода (лучше для долгих команд вроде fsck)
        process = subprocess.Popen(
            command_str,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            bufsize=1,  # Построчная буферизация
        )

        # Чтение и вывод в реальном времени
        for line in process.stdout:
            print(line, end="")

        process.wait()  # Ожидание завершения процесса

        if process.returncode == 0:
            print("\n--- Успешно ---")
            return True
        else:
            print(
                f"\n❌ Ошибка выполнения команды (Код возврата: {process.returncode})",
                file=sys.stderr,
            )
            return False

    except FileNotFoundError:
        print(
            f"❌ Ошибка: Команда или программа в '{command_str}' не найдена.",
            file=sys.stderr,
        )
        print(
            "Убедитесь, что git, cp, find, rm установлены и доступны в системном PATH.",
            file=sys.stderr,
        )
        return False
    except Exception as exc:
        print(f"❌ Неожиданная ошибка при выполнении: {command_str}", file=sys.stderr)
        print(f"Детали ошибки: {exc}", file=sys.stderr)
        return False


# --- Основная логика скрипта ---
def main():
    print("--- Запуск скрипта обслуживания Git ---")

    # Проверка: находимся ли мы в корне Git репозитория?
    if not os.path.isdir(GIT_DIR):
        print(f"❌ Ошибка: Каталог '{GIT_DIR}' не найден.", file=sys.stderr)
        print(
            "Пожалуйста, запустите этот скрипт из корневого каталога вашего Git репозитория.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Проверка, существует ли уже каталог бэкапа (возможно, от предыдущего неудачного запуска)
    if os.path.exists(BACKUP_DIR):
        print(
            f"⚠️ Предупреждение: Каталог резервной копии '{BACKUP_DIR}' уже существует.",
            file=sys.stderr,
        )
        print(
            f"Пожалуйста, удалите или переименуйте '{BACKUP_DIR}' вручную и повторите попытку.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Последовательное выполнение команд
    for cmd in COMMANDS:
        if not run_command(cmd):
            print("\n--- Скрипт прерван из-за ошибки ---", file=sys.stderr)

            if os.path.exists(BACKUP_DIR) and not cmd.startswith("rm -rf"):
                print(
                    f"ℹ️ Каталог резервной копии '{BACKUP_DIR}' мог быть создан и оставлен нетронутым.",
                    file=sys.stderr,
                )

            sys.exit(1)  # Выход с кодом ошибки

    print("\n--- Скрипт обслуживания Git успешно завершен ---")
    sys.exit(0)  # Выход с кодом успеха


if __name__ == "__main__":
    main()
