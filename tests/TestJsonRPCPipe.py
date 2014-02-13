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
        self.assertIsInstance(expected, str)
        self.assertIsInstance(result, str)

        expected, result = simplejson.loads(expected), simplejson.loads(result)
        if isinstance(expected, list):
            self.assertCountEqual(expected, result)
            for e, r in zip(expected, result):
                self.assertDictEqual(e, r)
        else:
            self.assertDictEqual(expected, result)

    def test_single_successful_request(self):
        self.request.set('q', '{"jsonrpc": "2.0", "method": "substract", "params": [42, 23], "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 19, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

        self.request.set('q', '{"jsonrpc": "2.0", "method": "add", "params": [42, 23], "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 65, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_invalid_request(self):
        self.request.set('q', '{}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

        self.request.set('q', '1')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

        self.request.set('q', '{"foo": "boo"}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )


    def test_invalid_batch_request(self):
        self.request.set('q', '[]')
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

    def test_invalid_params(self):
        self.request.set('q', '{"jsonrpc": "2.0", "method": "substract", "params": [], "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    # def test_server_error(self):
    #     self.request.set('q', '{"jsonrpc": "2.0", "method": "throw_server_error", "params": [], "id": 1}')
    #     self.assertCountEqual(
    #         loads('{"jsonrpc": "2.0", "error": {"code": -32001, "message": "Server error"}, "id": 1}'),
    #         loads(JsonRpcPipe.response('{"jsonrpc": "2.0", "method": "subtract", "params": [], "id": 1}', method))
    #     )
    #

    def test_valid_custom_batch(self):
        self.request.set('q', """
                [
                    {},
                    {"jsonrpc": "2.0", "method": "add", "params": [1, 2], "id": 1},
                    {"jsonrpc": "2.0", "method": "substract", "params": [1, 2], "id": 2}
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

    def test_notifications(self):
        self.request.set('q', '{"jsonrpc": "2.0", "method": "add", "params": [42, 23]}')
        self.assertEqual(
            '',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_method_not_found(self):
        self.request.set('q', '{"jsonrpc": "2.0", "method": "qwerty", "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found"}, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_params_in_request(self):
        self.request.set('q', '{"jsonrpc": "2.0", "method": "add_a_b", "params": {"a": 2, "b": 3}, "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": 5, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )

    def test_omitted_params(self):
        self.request.set('q', '{"jsonrpc": "2.0", "method": "dummy_action", "id": 1}')
        self.assertJsonEqual(
            '{"jsonrpc": "2.0", "result": null, "id": 1}',
            self.pipe.process(self.controller, self.application, self.request, None, None)
        )
