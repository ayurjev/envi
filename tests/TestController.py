import unittest
from envi import Application, Controller, StaticPipe
from io import BufferedReader, BytesIO

class UsersController(Controller):
    """ Пример контроллера действий над пользователями """
    default_action = "show"

    def setup(self, **kwargs):
        return {}

    @staticmethod
    def show(**kwargs):
        return "show users"

class TestController(unittest.TestCase):
    def setUp(self):
        self.app = Application()
        self.app.catchall = False
        self.test_response = lambda response_code, content_type: None
        self.app.set_static_pipe_output_converter(lambda cb: cb())

    def test_set_converter(self):
        """ Проверяю что установленный конвертор работает """
        converter = lambda cb: "%s %s" % (cb(), "append")

        self.app.set_static_pipe_output_converter(converter)
        self.assertEqual("static content append", StaticPipe.converter(lambda: "static content"))

    def test_routing(self):
        """
            Проверка работы роутинга
        """
        self.app.route("/users", UsersController)
        self.app.route("/users/<action>", UsersController)

        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/show/", "wsgi.input": BufferedReader(BytesIO())}, self.test_response))
        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/", "wsgi.input": BufferedReader(BytesIO())}, self.test_response))

        self.assertRaises(NotImplementedError, self.app, {"REQUEST_METHOD": "GET", "PATH_INFO": "/users/test/", "wsgi.input": BufferedReader(BytesIO())}, self.test_response)
