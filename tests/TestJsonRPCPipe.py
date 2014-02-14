import unittest
import simplejson
from envi import JsonRpcPipe, Request, Application
from tests.Controllers import BaseController


class TestJsonRpcPipe(unittest.TestCase):
    def setUp(self):
        self.pipe = JsonRpcPipe()
        self.request = Request()
        self.controller = BaseController()
        self.application = Application()

    def assertJsonEqual(self, expected, result):
        assert isinstance(expected, str)
        assert isinstance(result, str)

        expected, result = simplejson.loads(expected), simplejson.loads(result)
        if isinstance(expected, list):
            self.assertCountEqual(expected, result)
            for e, r in zip(expected, result):
                self.assertDictEqual(e, r)
        else:
            self.assertDictEqual(expected, result)

    def test_valid_request(self):
        """ Корректный ответ на один запрос """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 19, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

        self.request.set('q', '{"jsonrpc": "2.0", "method": "add", "params": [42, 23], "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 65, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_mixed_batch_request(self):
        """ Корректный ответ на пачку запросов """
        self.request.set('q', """
                [
                    {},
                    {"jsonrpc": "2.0", "method": "subtract", "params": [1, 2]},
                    {"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": 1},
                    {"jsonrpc": "2.0", "method": "subtract", "params": [1, 2], "id": 2}
                ]
        """)
        self.assertJsonEqual(
            """
            [
                {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},
                {"jsonrpc": "2.0", "result": 3, "id": 1},
                {"jsonrpc": "2.0", "result": -1, "id": 2}
            ]
            """,
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_empty_request(self):
        """ Корректный ответ на пустой запрос """
        self.request.set('q', '{}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

        self.request.set('q', '[]')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_unstructured_request(self):
        """ Корректный ответ на запрос, который не является JSON объектом или списком """
        self.request.set('q', '1')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

        self.request.set('q', '[1,2,3]')
        self.assertJsonEqual(
            """ [
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},
                    {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}
                ]
            """,
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_unformal_request(self):
        """ Корректный ответ на запрос без указания версии jsonrpc """
        self.request.set('q', '{"foo": "boo", "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_invalid_params(self):
        """ Корректный ответ если в запросе недостаточно параметров """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "subtract", "params": [], "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_notification_without_error(self):
        """ Ответ на уведомление без ошибки """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "add", "params": [42, 23]}')
        self.assertEqual(
            '',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_notification_with_error(self):
        """ Ответ на уведомление с ошибкой """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "qwerty"}')
        self.assertEqual(
            '',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_method_not_found(self):
        """ Корректный ответ на запрос к несуществующему методу """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "qwerty", "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_server_error(self):
        """ Корректный ответ для явно не отловленных исключений """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "divide", "params": {"dividend": 1, "divisor": 0}, "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32000, "message": "Server error"}, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )


    def test_params_in_request(self):
        """ Параметры в виде словаря доступны напрямую из request (см. реализацию действия add_a_b) """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "add_a_b", "params": {"a": 2, "b": 3}, "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 5, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_omitted_params(self):
        """ Корректный ответ на запрос с опущенными параметрами """
        self.request.set('q', '{"jsonrpc": "2.0", "method": "dummy_action", "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": null, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )
