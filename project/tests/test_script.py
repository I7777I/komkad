"""unit-тест модуля script."""

# импорт стандартных библиотек
import os
import sys
import unittest
from hashlib import sha256
from pathlib import Path
# Импорт вспомогательных функций и классов
from unittest.mock import AsyncMock, MagicMock, patch
from zipfile import ZipFile

sys.path.append('./')

# Импорт локальных модулей
from project.script import (  # noqa: E402
    calculate_sha256,
    calculate_sha256_for_zip_files,
    download_part,
    main,
)


class TestCalculateSha256(unittest.TestCase):
    """Тестирование функции `calculate_sha256`."""

    def setUp(self) -> None:  # noqa: ANN101
        """Создаём временный файл."""
        with open('test.txt', 'wb') as filename:
            filename.write(b'Hello, world!')
        self.temp_file = open('test.txt', 'rb')
        self.name = self.temp_file.name.split('\\')[-1]

    def tearDown(self) -> None:  # noqa: ANN101
        """Удаляем временный файл."""
        self.temp_file.close()
        if os.path.exists(self.name):
            os.remove(self.name)

    def test_calculate_sha256(self) -> None:  # noqa: ANN101
        """Тест, что возвращает корректный ХЭШ 256."""
        expected_hash = sha256(self.temp_file.read()).hexdigest()
        # Проверяем, что функция возвращает такой же хэш
        calculated_hash = calculate_sha256(self.name)
        self.assertEqual(expected_hash, calculated_hash)  # noqa: PT009


class TestCalculateSha256ForZipFiles(unittest.TestCase):
    """Тестирование функции `calculate_sha256_for_zip_files`."""

    def setUp(self: object) -> None:
        """Создаём тестовый ZIP-архив."""
        self.test_zip_file = 'test.zip'
        self.temp_dir = Path('./temp/')
        # Создание новой директории
        self.temp_dir.mkdir(parents=True, exist_ok=True)
        self.expected_hashes = {}

        # Создаем тестовый ZIP-архив с известными хэшами
        with ZipFile(f'./temp/{self.test_zip_file}', 'w') as zip_file:
            zip_file.writestr('file1', b'somedata')
            zip_file.writestr('file2', b'moredata')

        # Открываем ZIP-архив для чтения
        with ZipFile(f'./temp/{self.test_zip_file}', 'r') as zip_ref:
            zip_ref.extractall(f'{self.temp_dir}')
        for files in os.walk(f'{self.temp_dir}'):
            for file_name in files[2]:
                with open(f'{self.temp_dir}/{file_name}', 'rb') as f1:
                    self.expected_hashes[file_name] = sha256(
                        f1.read(),
                    ).hexdigest()

    def test_calculate_sha256_for_zip_files(self) -> None:  # noqa: ANN101
        """Тест, что возвращает корректный словарь."""
        actual_hashes = calculate_sha256_for_zip_files(
            str(self.temp_dir),
            self.test_zip_file,
        )
        self.assertDictEqual(  # noqa: PT009
            actual_hashes, self.expected_hashes,
        )

    def tearDown(self) -> None:  # noqa: ANN101
        """Удаляем созданный тестовый ZIP-архив."""
        for file_name in os.listdir(self.temp_dir):
            os.remove(os.path.join(self.temp_dir, file_name))
        # удаляем директорию temp с тестовым архивом данных
        os.rmdir(self.temp_dir)


class TestDownloadPart(unittest.IsolatedAsyncioTestCase):
    """Тестирование функции download_part."""

    def setUp(self) -> None:  # noqa: ANN101
        """Создаём тестовый URL."""
        self.url = 'https://example.com/'
        self.part_index = 0
        self.expected_content = [b'testdata']
        self.actual_content = ['']

    async def test_download_part(self) -> None:  # noqa: ANN101
        """Тест, что добавляет в список части файла."""
        with patch('aiohttp.ClientSession') as mock_session:
            response_mock = AsyncMock()
            response_mock.read.return_value = b'testdata'
            get_mock = MagicMock()
            get_mock.return_value.__aenter__.return_value = response_mock
            mock_session.get = get_mock
            await download_part(
                mock_session,
                self.url,
                self.part_index,
                self.actual_content,
            )
            self.assertEqual(  # noqa: PT009
                self.expected_content, self.actual_content,
            )


class TestMain(unittest.IsolatedAsyncioTestCase):
    """Тестирование функции main."""

    @staticmethod
    async def new_download_part(
        session: object,
        url: str,
        part_index: int,
        content_list: list,
    ) -> None:
        """
        Функция для замены функции download_part в классе TestMain.

        Args:
            session: объект класса aiohttp.ClientSession
            url: адрес скачиваемого файла
            part_index: индекс скачиваемого файла
            content_list: содержимое файла
        """
        content_list[part_index] = b'testcase'

    @staticmethod
    def new_calculate_sha256_for_zip_files(*args: tuple) -> dict:
        """
        Функция для замены функции calculate_sha256_for_zip_files.

        Args:
            args: замена неиспользуемых аргументов

        Returns:
            Словарь с ключами из названия файла и значением хэш-файлы sha256
        """
        hash_file = calculate_sha256('file2.txt')
        return {'file2.txt': hash_file}

    def setUp(self) -> None:  # noqa: ANN101
        """Создаём объект класса TestMain."""
        self.filename = 'file2.txt'
        with open(self.filename, 'wb') as output_file:
            data_to_write = b'testcase'
            output_file.write(data_to_write)

    @patch(
        'project.script.calculate_sha256_for_zip_files',
        new=new_calculate_sha256_for_zip_files,
    )
    @patch('project.script.download_part', new=new_download_part)
    async def test_main(self) -> None:  # noqa: ANN101
        """Проверяем, что функция main вызывает соответствующие методы."""
        await main()

    def tearDown(self) -> None:  # noqa: ANN101
        """Удаляем созданный файл."""
        os.remove(self.filename)


class TestMainError(unittest.IsolatedAsyncioTestCase):
    """Тестирование функции main на обработку исключений."""

    @staticmethod
    async def new_download_part(*args: tuple) -> None:
        """
        Функция для замены функции download_part в классе TestMainError.

        Args:
            args: замена неиспользуемых аргументов

        Raises:
            Exception: если сервер возвращает код состояния, отличный от 200.
                       если возникли проблемы с подключением к серверу.
                       если аргументы функции некорректны.
        """
        raise Exception

    @staticmethod
    async def new_download_part_1(*args: tuple) -> None:
        """
        Функция для замены функции download_part в классе TestMain.

        Args:
            args: замена неиспользуемых аргументов
        """

    @staticmethod
    async def new_calculate_sha256_for_zip_files(*args: tuple) -> None:
        """
        Функция для замены calculate_sha256_for_zip_files в  TestMainError.

        Args:
            args: замена неиспользуемых аргументов

        Raises:
            Exception: если файл не является zip-файлом.
                       если не удалось прочитать ХЭШи файлов.
                       если аргументы функции некорректны.
        """
        raise Exception  # pragma: no cover

    @patch('project.script.download_part', new=new_download_part)
    async def test_main_error_read(self) -> None:  # noqa: ANN101
        """Тест, что функция main обрабатывает исключение при скачивании."""
        await main()

    @patch('project.script.download_part', new=new_download_part_1)
    @patch(
        'project.script.calculate_sha256_for_zip_files',
        new=new_calculate_sha256_for_zip_files,
    )
    async def test_main_error_write(self) -> None:  # noqa: ANN101
        """Тест, что функция main обрабатывает исключение при записи."""
        await main()


if __name__ == '__main__':  # pragma: no cover
    unittest.main()
