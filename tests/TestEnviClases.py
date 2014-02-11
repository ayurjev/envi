import unittest
import bottle
import envi
from envi import Application, Controller


class TestController(Controller):
    default_action = "index"

    def setup(self, app, request, user, host):
        return 1

    @staticmethod
    def index(app, request, user, host, domain_data):
        return app, request, user, host, domain_data


class UsersTestController(Controller):
    """ Пример контроллера действий над пользователями """
    default_action = "show"

    def setup(self, app, request, user, host):
        pass

    @staticmethod
    def show(app, request, user, host, data):
        return "show users"


class User(object):
    pass


test_response = lambda response_code, content_type: None

class TestControllerInput(unittest.TestCase):
    def setUp(self):
        self.app = Application()

    def test_set_converter(self):
        """ Проверяю что установленный конвертор работает """
        converter = lambda cb: "%s %s" % (cb(), "append")

        self.app.set_static_pipe_output_converter(converter)
        self.app.set_ajax_pipe_output_converter(converter)
        self.app.set_pjax_pipe_output_converter(converter)
        self.app.set_jsonrpc_pipe_output_converter(converter)

        self.assertEqual("static content append", envi.StaticPipe.converter(lambda: "static content"))
        self.assertEqual("ajax content append", envi.AjaxPipe.converter(lambda: "ajax content"))
        self.assertEqual("pjax content append", envi.PjaxPipe.converter(lambda: "pjax content"))
        self.assertEqual("jsonrpc content append", envi.JsonRpcPipe.converter(lambda: "jsonrpc content"))

    # def test_controller_input_data(self):
    #     """ Проверяю что метод контроллера получает данные """
    #     self.app.route("/", TestController)
    #
    #     app, request, user, host = self.app, bottle.request, None, None
    #     domain_data = TestController().setup(app, request, user, host)
    #
    #     # Вызов роутера внутри bottle app
    #     self.assertEqual((app, request, user, host, domain_data), self.app.routes[-1].call())
    #
    #     user = User()
    #     self.app.set_user_initialization_hook(lambda: user)
    #
    #     self.assertEqual((app, request, user, host, domain_data), self.app.routes[-1].call())


    def test_routing(self):
        """
            Проверка работы роутинга
        """
        self.app.route("/users", UsersTestController)
        self.app.route("/users/<action>", UsersTestController)

        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/show/"}, test_response))
        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/"}, test_response))

        self.app.catchall = False
        self.app.set_ajax_pipe_output_converter(lambda cb: cb())
        self.assertRaises(NotImplementedError, self.app, {"REQUEST_METHOD": "GET", "PATH_INFO": "/users/test/"}, test_response)


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
