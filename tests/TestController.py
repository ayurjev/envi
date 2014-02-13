import unittest
from envi import Application, StaticPipe, AjaxPipe, PjaxPipe, JsonRpcPipe
from tests.Controllers import BaseController, UsersController
from io import BufferedReader, BytesIO

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
        self.app.set_ajax_pipe_output_converter(converter)
        self.app.set_pjax_pipe_output_converter(converter)
        self.app.set_jsonrpc_pipe_output_converter(converter)

        self.assertEqual("static content append", StaticPipe.converter(lambda: "static content"))
        self.assertEqual("ajax content append", AjaxPipe.converter(lambda: "ajax content"))
        self.assertEqual("pjax content append", PjaxPipe.converter(lambda: "pjax content"))
        self.assertEqual("jsonrpc content append", JsonRpcPipe.converter(lambda: "jsonrpc content"))

    # def test_controller_input_data(self):
    #     class User(object):
    #         pass
    #     """ Проверяю что метод контроллера получает данные """
    #     self.app.route("/", BaseController)
    #
    #     app, request, user, host = self.app, bottle.request, None, None
    #     domain_data = BaseController().setup(app, request, user, host)
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
        self.app.route("/users", UsersController)
        self.app.route("/users/<action>", UsersController)

        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/show/", "wsgi.input": BufferedReader(BytesIO())}, self.test_response))
        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/", "wsgi.input": BufferedReader(BytesIO())}, self.test_response))

        self.assertRaises(NotImplementedError, self.app, {"REQUEST_METHOD": "GET", "PATH_INFO": "/users/test/", "wsgi.input": BufferedReader(BytesIO())}, self.test_response)
