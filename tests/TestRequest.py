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

    def test_ajax_type_detection(self):
        """ Ajax запрос определяется по заголовку HTTP_X_REQUESTED_WITH """
        request = envi.Request(environ={"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(envi.Request.Types.AJAX, request.type())

    def test_pjax_type_detection(self):
        """ Pjax запрос определяется по двум заголовкам HTTP_X_REQUESTED_WITH и HTTP_X_PJAX """
        request = envi.Request(environ={"HTTP_X_PJAX": True, "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(envi.Request.Types.PJAX, request.type())

    def test_json_rpc_type_detection(self):
        """ JsonRPC запрос определяется по наличию аргумента q в запросе и только по нему одному """
        request = envi.Request({"q": "{}"})
        self.assertEqual(envi.Request.Types.JSON_RPC, request.type())

        request = envi.Request({"q": "{}"}, environ={"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(envi.Request.Types.JSON_RPC, request.type())

    def test_static_type_detection(self):
        """ Любой запрос не являющийся Ajax, Pjax, Json_RPC является STATIC """
        request = envi.Request()
        self.assertEqual(envi.Request.Types.STATIC, request.type())
