"""Этот Script написан для скачивания git репозитория.

Скрипт скачивает zip-файл асинхронно, в 3 одновременных задачи,
содержимое HEAD репозитория
https://gitea.radium.group/radium/project-configuration во временную папку.

После выполнения всех асинхронных задач скрипт  считает sha256 хэши
от каждого файла.
"""

# импорт стандартных библиотек
import asyncio
import hashlib
import os
import tempfile
import zipfile

# импорты сторонних библиотек
import aiohttp

# Параметры для разбиения файла
CHUNK_SIZE = 1024  # Размер одной части в байтах
TOTAL_PARTS = 3  # Общее количество частей
URL = 'https://gitea.radium.group/radium/project-configuration/archive/master.zip'  # noqa: E501

async def download_part(
    session: object,
    url: str,
    part_index: int,
    file_parts: list,
) -> None:
    """Скачивает часть файла по url и помещает в список file_parts.

    Args:
        session: созданная сессия для скачивания файла.
        url: URL для скачивания.
        part_index: номер части в файле.
        file_parts: список частей файла.
    """
    async with session.get(
        url +
        '?range=' +
        str(part_index * CHUNK_SIZE) +
        '-' +
        str((part_index + 1) * CHUNK_SIZE),
    ) as response:
        content_part = await response.read()
        file_parts[part_index] = content_part


def calculate_sha256(file_path: str) -> str:
    """Возвращает SHA-256 хэш файла расположенного по пути file_path.

    Args:
        file_path: путь до файла.

    Returns:
        SHA-256 хэш файла расположенного по пути file_path.
    """
    with open(file_path, 'rb') as hashed_file:
        hash_of_file = hashed_file.read()
    return hashlib.sha256(hash_of_file).hexdigest()


def calculate_sha256_for_zip_files(  # noqa: WPS210
    directory_path: str,
    zip_file: object,
) -> dict:
    """Возвращает список SHA-256 хэшей для всех файлов в директории.

    Args:
        directory_path: путь до директории с файлами.
        zip_file: имя ZIP-архива.

    Returns:
        SHA-256 хэшей для всех файлов в директории.
    """
    with zipfile.ZipFile(
        f'{directory_path}\\{zip_file}',  # noqa: WPS305
        'r',
    ) as zip_f:
        zip_f.extractall(directory_path)
    sha256_hashes = {}
    for root, _, files in os.walk(directory_path):
        for file_name in files:
            file_path = os.path.join(root, file_name)
            sha256_hashes[file_name] = calculate_sha256(file_path)
    print(sha256_hashes)  # noqa: WPS421
    return sha256_hashes


def write_file(filename: str, file_parts: list) -> None:
    """Записывает ZIP-файл и определяет ХЭШ файлов."""
    try:
        # создаём временную дирректорию
        with tempfile.TemporaryDirectory(dir='./') as temp_dir:
            # создаём временный файл
            with open(
                f'{temp_dir}\\{filename}',  # noqa: WPS305
                'ab',
            ) as file_to_write:
                # собираем файл из частей
                for _ in file_parts:
                    file_to_write.write(_)
                # вычисляем ХЭШ файлов в ZIP-архивe
                calculate_sha256_for_zip_files(temp_dir, filename)
    except Exception as error:
        print(  # noqa: WPS421
            'Ошибка при открытии или записи файла: ',
            error.__class__.__name__,
        )
    else:
        print('\nФайл успешно прочитан\n')  # noqa: WPS421


async def main() -> None:
    """Создаем сессию для асинхронного скачивания."""
    # Устанавливаем имя скачанного ZIP-архива
    filename = URL.split('/')[-1]
    file_parts = [0 for _ in range(TOTAL_PARTS)]
    try:
        async with aiohttp.ClientSession() as session:
            # Создаем задачи для одновременного скачивания частей файл
            tasks = [
                asyncio.create_task(
                    download_part(session, URL, part, file_parts),
                )
                for part in range(TOTAL_PARTS)
            ]
            await asyncio.gather(*tasks)
    except Exception as error1:
        print(  # noqa: WPS421
            'Ошибка при скачивании: ',
            error1.__class__.__name__,
        )
    else:
        print('\nФайл успешно скачан и записан\n')  # noqa: WPS421
    write_file(filename, file_parts)


if __name__ == '__main__':  # pragma: no cover
    # Получаем цикл событий
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    # Запускаем функцию main до завершения
    loop.run_until_complete(main())
    # Закрываем цикл событий
    loop.close()
