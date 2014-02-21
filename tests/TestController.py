import unittest
from webtest import TestApp
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
        self.test_app = TestApp(self.app)

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


    def test_headers(self):
        class TestControl(Controller):
            def setup(self, app, request, user, host) -> dict:
                return {}

            @staticmethod
            def index(request, **kwargs):
                request.response.add_header("HTTP_X_TEST", 111)

        self.app.route("/<action>/", TestControl)
        self.assertEqual("111", self.test_app.get("/index/").headers['http-x-test'])


class TestApplication(unittest.TestCase):
    def setUp(self):
        self.app = Application()
        self.app.set_static_pipe_output_converter(lambda cb: cb())
        self.test_app = TestApp(self.app)

    def test_redirect(self):
        class RedirectController(Controller):
            def setup(self, **kwargs):
                return {}

            @staticmethod
            def redirect(app, **kwargs):
                app.redirect("http://localhost/test/")

        self.app.route("/<action>/", RedirectController)
        self.assertEquals('http://localhost/test/', self.test_app.get("/redirect/").headers['Location'])
        self.assertEquals('302 Found', self.test_app.get("/redirect/").status)
