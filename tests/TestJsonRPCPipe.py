import unittest
import json
from webtest import TestApp
from envi import Application, Controller


class JsonRpcController(Controller):
    default_action = "index"

    def setup(self, **kwargs):
        return {}

    @staticmethod
    def index(app, request, user, host, domain_data):
        return app, request, user, host, domain_data

    @staticmethod
    def subtract(request, **kwargs):
        if len(request.get("params")) < 2:
            raise request.RequiredArgumentIsMissing()

        return request.get("params")[0] - request.get("params")[1]

    @staticmethod
    def add(request, **kwargs):
        if len(request.get("params")) < 2:
            raise request.RequiredArgumentIsMissing()

        return sum(request.get("params"))

    @staticmethod
    def add_a_b(request, **kwargs):
        return request.get('a') + request.get('b')

    @staticmethod
    def divide(request, **kwargs):
        return request.get('dividend') / request.get('divisor')

    @staticmethod
    def dummy_action(**kwargs):
        pass


class TestJsonRpcPipe(unittest.TestCase):
    def setUp(self):
        app = Application()
        app.route("/", JsonRpcController)
        self.test_app = TestApp(app)

    def assertJsonEqual(self, expected, result):
        assert isinstance(expected, str)
        assert isinstance(result, str)

        expected, result = json.loads(expected), json.loads(result)
        if isinstance(expected, list):
            self.assertCountEqual(expected, result)
            for e, r in zip(expected, result):
                self.assertDictEqual(e, r)
        else:
            self.assertDictEqual(expected, result)

    def test_valid_request(self):
        """ Корректный ответ на один запрос """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 19, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}'}).body.decode()
        )

        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 65, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "add", "params": [42, 23], "id": 1}'}).body.decode()
        )

    def test_invalid_method(self):
        """ Корректный ответ на запрос в котором имя метода не является строкой """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": 1, "params": 2, "id": 1}'}).body.decode()
        )

    def test_mixed_batch_request(self):
        """ Корректный ответ на пачку запросов """
        self.assertJsonEqual(
            """
            [
                {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},
                {"jsonrpc": "2.0", "result": 3, "id": 1},
                {"jsonrpc": "2.0", "result": -1, "id": 2}
            ]
            """,
            self.test_app.get("/", params={'q': """
            [
                {},
                {"jsonrpc": "2.0", "method": "subtract", "params": [1, 2]},
                {"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": 1},
                {"jsonrpc": "2.0", "method": "subtract", "params": [1, 2], "id": 2}
            ]
            """}).body.decode()
        )

    def test_empty_request(self):
        """ Корректный ответ на пустой запрос """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.test_app.get("/", params={'q': '{}'}).body.decode()
        )

        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.test_app.get("/", params={'q': '[]'}).body.decode()
        )

    def test_unstructured_request(self):
        """ Корректный ответ на запрос, который не является JSON объектом или списком """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.test_app.get("/", params={'q': '1'}).body.decode()
        )

        self.assertJsonEqual(
            """ [
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}
                ]
            """,
            self.test_app.get("/", params={'q': '[1,2,3]'}).body.decode()
        )

    def test_unformal_request(self):
        """ Корректный ответ на запрос без указания версии jsonrpc """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": 1}',
            self.test_app.get("/", params={'q': '{"foo": "boo", "id": 1}'}).body.decode()
        )

    def test_not_enough_params(self):
        """ Корректный ответ когда запросе недостаточно параметров (может стоит в этом случае кидать server error?) """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "subtract", "params": [], "id": 1}'}).body.decode()
        )

    def test_really_invalid_params(self):
        """ Корректный ответ на запрос в котором параметры заданы не списком и не объектом """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "subtract", "params": 2, "id": 1}'}).body.decode()
        )

    def test_notification_without_error(self):
        """ Ответ на уведомление без ошибки """
        self.assertEqual(
            '',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "add", "params": [42, 23]}'}).body.decode()
        )

    def test_notification_with_error(self):
        """ Ответ на уведомление с ошибкой """
        self.assertEqual(
            '',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "qwerty"}'}).body.decode()
        )

    def test_method_not_found(self):
        """ Корректный ответ на запрос к несуществующему методу """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "qwerty", "id": 1}'}).body.decode()
        )

    def test_server_error(self):
        """ Корректный ответ для явно не отловленных исключений """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32000, "message": "Server error"}, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "divide", "params": {"dividend": 1, "divisor": 0}, "id": 1}'}).body.decode()
        )

    def test_params_in_request(self):
        """ Параметры в виде словаря доступны напрямую из request (см. реализацию действия add_a_b) """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 5, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "add_a_b", "params": {"a": 2, "b": 3}, "id": 1}'}).body.decode()
        )

    def test_omitted_params(self):
        """ Корректный ответ на запрос с опущенными параметрами """
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": null, "id": 1}',
            self.test_app.get("/", params={'q': '{"jsonrpc": "2.0", "method": "dummy_action", "id": 1}'}).body.decode()
        )
