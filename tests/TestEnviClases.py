import unittest
import bottle
from envi import Application, Controller
from webtest import TestApp
import pipes


class TestController(Controller):
    default_action = "index"

    def setup(self, app, request, user, host):
        return 1

    @staticmethod
    def index(app, request, user, host, domain_data):
        return app, request, user, host, domain_data


class User(object):
    pass

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

        self.assertEqual("static content append", pipes.StaticPipe.converter(lambda: "static content"))
        self.assertEqual("ajax content append", pipes.AjaxPipe.converter(lambda: "ajax content"))
        self.assertEqual("pjax content append", pipes.PjaxPipe.converter(lambda: "pjax content"))
        self.assertEqual("jsonrpc content append", pipes.JsonRpcPipe.converter(lambda: "jsonrpc content"))

    def test_controller_input_data(self):
        """ Проверяю что метод контроллера получает данные """
        self.app.route("/", TestController)

        app, request, user, host = self.app, bottle.request, None, None
        domain_data = TestController().setup(app, request, user, host)

        # Вызов роутера внутри bottle app
        self.assertEqual((app, request, user, host, domain_data), self.app.routes[-1].call())

        user = User()
        self.app.set_user_initialization_hook(lambda: user)

        self.assertEqual((app, request, user, host, domain_data), self.app.routes[-1].call())

