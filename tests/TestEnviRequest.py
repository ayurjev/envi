import unittest
from webtest import TestApp
from envi import Application, Controller


class RequestController(Controller):
    def setup(self, **kwargs):
        return {}

    @staticmethod
    def return_arg(request, **kwargs):
        return request.get('arg')

    @staticmethod
    def return_file(request, **kwargs):
        return request.get('arg').file.read()


class TestEnviRequest(unittest.TestCase):
    def setUp(self):
        self.app = Application()
        self.app.catchall = False
        self.app.set_ajax_pipe_output_converter(lambda cb: cb())

        self.test_app = TestApp(self.app)

    def test_request_get_arguments(self):
        """ Request содержит в себе GET параметры """
        self.app.route("/<action>/", RequestController)
        self.assertEqual(b"123", self.test_app.get("/return_arg/", {'arg': '123'}).body)

    def test_request_post_arguments(self):
        """ Request содержит в себе POST параметры """
        self.app.route("/<action>/", RequestController)
        self.assertEqual(b"123", self.test_app.post("/return_arg/", {'arg': '123'}).body)

    def test_request_files_arguments(self):
        """ Request содержит в себе FILES """
        self.app.route("/<action>/", RequestController)
        self.assertEqual(b"FILE CONTENT", self.test_app.post("/return_file/", upload_files=[('arg', 'text/plain', b'FILE CONTENT')]).body)

    def test_multibyte_request_params(self):
        """ Контроллер умеет принимать параметры в multi-byte кодировке """
        self.app.route("/<action>/<arg>/", RequestController)
        self.assertEqual("параметр".encode(), self.test_app.get(None, extra_environ={'PATH_INFO': "/return_arg/параметр/".encode().decode("iso-8859-1")}).body)
