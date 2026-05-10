import unittest
from unittest.mock import patch

from app.catalog import repository


class FakeCursor:
    def __init__(self, rows):
        self.rows = rows
        self.query = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def execute(self, query):
        self.query = query

    def fetchall(self):
        return self.rows


class FakeConnection:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False

    def cursor(self):
        return FakeCursor(self.rows)


class CatalogRepositoryTest(unittest.TestCase):
    def setUp(self):
        repository.load_catalog.cache_clear()

    def tearDown(self):
        repository.load_catalog.cache_clear()

    def test_load_catalog_reads_methods_and_templates_from_postgres(self):
        rows = [
            (
                1,
                "pomodoro",
                "Pomodoro",
                "Работа короткими сессиями.",
                "Задачи на концентрацию.",
                "распределение времени",
                "задает ритм фокус-сессий",
                '{"steps": [{"title": "Начать"}], "schedule_hint": "Работать фокус-сессиями."}',
            )
        ]

        with patch.object(repository.psycopg, "connect", return_value=FakeConnection(rows)):
            catalog = repository.load_catalog()

        self.assertEqual(catalog["methods"][0]["code"], "pomodoro")
        self.assertEqual(catalog["methods"][0]["name"], "Pomodoro")
        self.assertEqual(catalog["methods"][0]["group"], "распределение времени")
        self.assertEqual(catalog["methods"][0]["role"], "задает ритм фокус-сессий")
        self.assertEqual(catalog["templates"]["pomodoro"]["steps"][0]["title"], "Начать")
        self.assertEqual(catalog["templates"]["pomodoro"]["schedule_hint"], "Работать фокус-сессиями.")

    def test_load_catalog_fails_when_database_has_no_templates(self):
        with patch.object(repository.psycopg, "connect", return_value=FakeConnection([])):
            with self.assertRaisesRegex(RuntimeError, "нет методов"):
                repository.load_catalog()


if __name__ == "__main__":
    unittest.main()
