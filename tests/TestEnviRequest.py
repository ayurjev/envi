import unittest
from envi import Application
from tests.Controllers import RequestController
from io import BufferedReader, BytesIO


class TestController(unittest.TestCase):
    def setUp(self):
        self.app = Application()
        self.app.catchall = False
        self.test_response = lambda response_code, content_type: None
        self.app.set_ajax_pipe_output_converter(lambda cb: cb())

    def test_request_get_arguments(self):
        """ Request содержит в себе GET параметры """
        self.app.route("/<action>/", RequestController)
        self.assertEqual([b"123"], self.app({"REQUEST_METHOD": "GET", "PATH_INFO": "/get_arg/", "QUERY_STRING": "arg=123", "wsgi.input": BufferedReader(BytesIO())}, self.test_response))

    def test_request_post_arguments(self):
        """ Request содержит в себе POST параметры """
        body = b"arg=123"
        self.app.route("/<action>/", RequestController)
        self.assertEqual([b"123"], self.app({"REQUEST_METHOD": "POST", "PATH_INFO": "/get_arg/", "CONTENT_LENGTH": len(body), "wsgi.input": BufferedReader(BytesIO(body))}, self.test_response))

    def test_request_files_arguments(self):
        """ Request содержит в себе FILES """
        self.app.route("/<action>/", RequestController)

        body = b"-12345\r\nContent-Disposition: form-data; name=\"arg\"; filename=\"filename\"\r\nContent-Type: text/plain\r\n\r\nFILE CONTENT"
        self.assertEqual([b"FILE CONTENT"], self.app({
            "REQUEST_METHOD": "POST",
            "CONTENT_TYPE": "multipart/form-data; boundary=-12345",
            "PATH_INFO": "/get_file/",
            "CONTENT_LENGTH": len(body),
            "wsgi.input": BufferedReader(BytesIO(body))
        }, self.test_response))

    def test_multibyte_request_params(self):
        """ Контроллер умеет принимать параметры в multi-byte кодировке """
        self.app.route("/<action>/<arg>/", RequestController)
        self.assertEqual(["параметр".encode()], self.app({
            "REQUEST_METHOD": "GET",
            "PATH_INFO": "/get_arg/параметр/".encode().decode("iso-8859-1"),
            "wsgi.input": BufferedReader(BytesIO())
        }, self.test_response))