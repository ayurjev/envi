import unittest
import envi

class TestRequest(unittest.TestCase):
    def setUp(self):
        """ Каждый тест получает пустой объект запроса """
        self.request = envi.Request()

    def test_getter(self):
        """ Запрос инициализируется любым количеством словарей """
        request = envi.Request({'a': 1}, {'b': 2}, {'c': 3}, {'d': 4})
        self.assertEqual(1, request.get('a'))
        self.assertEqual(2, request.get('b'))
        self.assertEqual(3, request.get('c'))
        self.assertEqual(4, request.get('d'))

    def test_setter(self):
        """ Сеттер добавляет в запрос новый аргумент """
        self.request.set('argument', True)
        self.assertEqual(True, self.request.get('argument'))

    def test_update_from_dictionary(self):
        """ Запрос можно обновить данными из словаря """
        self.request.update({'a': 1, 'b': 2})
        self.assertEqual(1, self.request.get('a'))
        self.assertEqual(2, self.request.get('b'))

    def test_update_from_non_dictionary(self):
        """ Попытка обновить запрос не из словаря вызывает исключение """
        self.assertRaises(TypeError, self.request.update, 1)
        self.assertRaises(TypeError, self.request.update, [])

    def test_missing_argument_with_default_value(self):
        """ Запрос отсутствующего аргумента с указанием дефолтного значения возвращает переданное дефолтное значение """
        self.assertEqual(2, self.request.get('missing_argument_with_default_value', 2))

    def test_missing_argument(self):
        """ Запрос отсутствующего аргумента без указания дефолтного значения вызывает исключение """
        self.assertRaises(envi.Request.RequiredArgumentIsMissing, self.request.get, 'missing_argument')

    def test_missing_argument_with_none(self):
        """ Запрос отсутствующего аргумента с дефолтным значением None вызывает исключение """
        self.assertRaises(envi.Request.RequiredArgumentIsMissing, self.request.get, 'missing_argument', None)

    def test_override(self):
        """ Из нескольких значений аргумента в запросе сохранится последнее переданное """
        request = envi.Request({'prop': 1}, {'prop': 2})
        self.assertEqual(2, request.get('prop'))

        request.set('prop', 3)
        self.assertEqual(3, request.get('prop'))

        request.update({'prop': 4})
        self.assertEqual(4, request.get('prop'))
