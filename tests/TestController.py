import unittest
import bottle
import envi
from envi import Application
from tests.Controllers import RequestTestController, TestController, UsersTestController
from io import BufferedReader, BytesIO
import cgi

class TestController(unittest.TestCase):
    def setUp(self):
        self.app = Application()
        self.app.catchall = False
        self.test_response = lambda response_code, content_type: None
        self.app.set_ajax_pipe_output_converter(lambda cb: cb())

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

        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/show/", "wsgi.input": BufferedReader(BytesIO(b""))}, self.test_response))
        self.assertEqual([b"show users"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/users/", "wsgi.input": BufferedReader(BytesIO(b""))}, self.test_response))

        self.app.catchall = False
        self.assertRaises(NotImplementedError, self.app, {"REQUEST_METHOD": "GET", "PATH_INFO": "/users/test/", "wsgi.input": BufferedReader(BytesIO(b""))}, self.test_response)

    def test_request_get_arguments(self):
        """ Request содержит в себе GET параметры """
        self.app.route("/<action>/", RequestTestController)
        self.assertEqual([b"123"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/get_arg/", "QUERY_STRING": "arg=123", "wsgi.input": BufferedReader(BytesIO(b""))}, self.test_response))

    def test_request_post_arguments(self):
        """ Request содержит в себе POST параметры """
        body = b"arg=123"
        self.app.route("/<action>/", RequestTestController)
        self.assertEqual([b"123"], self.app({"REQUEST_METHOD": "POST", "PATH_INFO": "/get_arg/", "CONTENT_LENGTH": len(body), "wsgi.input": BufferedReader(BytesIO(body))}, self.test_response))

    def test_request_files_arguments(self):
        """ Request содержит в себе FILES """
        self.app.route("/<action>/", RequestTestController)

        body = b"-12345\r\nContent-Disposition: form-data; name=\"arg\"; filename=\"filename\"\r\nContent-Type: text/plain\r\n\r\nFILE CONTENT"
        self.assertEqual([b"FILE CONTENT"], self.app({
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": "multipart/form-data; boundary=-12345",
            "PATH_INFO": "/get_file/",
            "CONTENT_LENGTH": len(body),
            "wsgi.input": BufferedReader(BytesIO(body))
        }, self.test_response))

