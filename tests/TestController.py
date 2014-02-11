import unittest
import bottle
import envi
from envi import Application
from tests.Controllers import RequestTestController, TestController, UsersTestController


class TestController(unittest.TestCase):
    def setUp(self):
        self.app = Application()
        self.test_response = lambda response_code, content_type: None

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
    #     class User(object):
    #         pass
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

        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/show/"}, self.test_response))
        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/"}, self.test_response))

        self.app.catchall = False
        self.app.set_ajax_pipe_output_converter(lambda cb: cb())
        self.assertRaises(NotImplementedError, self.app, {"REQUEST_METHOD": "GET", "PATH_INFO": "/users/test/"}, self.test_response)

    def test_request_get_arguments(self):
        """ Request содержит в себе GET параметры """
        self.app.route("/")
