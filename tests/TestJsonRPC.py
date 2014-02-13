import unittest
from envi import JsonRPC
from simplejson import loads

class TestJsonRPC(unittest.TestCase):
    def test_single_successful_request(self):
        self.assertCountEqual(
            loads('{"jsonrpc": "2.0", "result": 19, "id": 1}'),
            loads(JsonRPC.response('{"jsonrpc": "2.0", "method": "subtract", "params": [42, 23], "id": 1}', cb=lambda a, b, action: a - b))
        )
        self.assertCountEqual(
            loads('{"jsonrpc": "2.0", "result": 65, "id": 1}'),
            loads(JsonRPC.response('{"jsonrpc": "2.0", "method": "add", "params": [42, 23], "id": 1}', cb=lambda a, b, action: a + b))
        )
        self.assertCountEqual(
            loads('{"jsonrpc": "2.0", "result": null, "id": 1}'),
            loads(JsonRPC.response('{"jsonrpc": "2.0", "method": "subtract", "params": [], "id": 1}', cb=lambda action: None))
        )

    def test_invalid_request(self):
        self.assertCountEqual(
            loads('{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}'),
            loads(JsonRPC.response('{}', lambda: None))
        )

    def test_invalid_params(self):
        self.assertCountEqual(
            loads('{"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 1}'),
            loads(JsonRPC.response('{"jsonrpc": "2.0", "method": "subtract", "params": [1, 2], "id": 1}', lambda action: None))
        )

    def test_server_error(self):
        def method():
            raise JsonRPC.ServerError(1)

        self.assertCountEqual(
            loads('{"jsonrpc": "2.0", "error": {"code": -32001, "message": "Server error"}, "id": 1}'),
            loads(JsonRPC.response('{"jsonrpc": "2.0", "method": "subtract", "params": [], "id": 1}', method))
        )

    def test_invalid_batch(self):
        self.assertCountEqual(
            loads('{"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null}'),
            loads(JsonRPC.response('[]', lambda action: None))
        )

    def test_valid_batch(self):
        self.assertCountEqual(
            loads("""
            [
                {"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request"}, "id": null},
                {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 1},
                {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}, "id": 2}
            ]
            """),
            loads(JsonRPC.response("""
                [
                    {},
                    {"jsonrpc": "2.0", "method": "subtract", "params": [1, 2], "id": 1},
                    {"jsonrpc": "2.0", "method": "subtract", "params": [1, 2], "id": 2}
                ]
            """, lambda action: None))
        )

        def sub_add(a, b, action):
            if action == 'add':
                return a + b
            elif action == 'substract':
                return a - b

        self.assertCountEqual(
            loads("""
            [
                {"jsonrpc": "2.0", "result": 19, "id": 1},
                {"jsonrpc": "2.0", "result": 65, "id": 2}
            ]
            """),
            loads(JsonRPC.response("""
                [
                    {"jsonrpc": "2.0", "method": "substract", "params": [42, 23], "id": 1},
                    {"jsonrpc": "2.0", "method": "add", "params": [42, 23], "id": 2}
                ]
            """, sub_add))
        )

