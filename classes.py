import bottle
import simplejson
from abc import ABCMeta, abstractmethod


class Application(bottle.Bottle):
    @staticmethod
    def user_initialization_hook():
        """
            Функция для инициализации пользователя приложения
        """

    @staticmethod
    def set_user_initialization_hook(cb):
        Application.user_initialization_hook = cb

    @staticmethod
    def set_static_pipe_output_converter(cb):
        StaticPipe.converter = cb

    @staticmethod
    def set_ajax_pipe_output_converter(cb):
        AjaxPipe.converter = cb

    @staticmethod
    def set_pjax_pipe_output_converter(cb):
        PjaxPipe.converter = cb

    @staticmethod
    def set_jsonrpc_pipe_output_converter(cb):
        JsonRpcPipe.converter = cb

    @staticmethod
    def _host():
        """ Предоставляет информацию о параметрах запроса """
        return {
            "ip": bottle.request.environ.get("REMOTE_ADDR"),
            "port": bottle.request.environ.get("SERVER_PORT"),
            "user_agent": bottle.request.environ.get("HTTP_USER_AGENT"),
        }

    # noinspection PyMethodOverriding
    def route(self, path, controller):
        app = self

        def wrapper(*args, **kwargs):
            request = Request(kwargs, dict(bottle.request.GET.decode()), dict(bottle.request.POST.decode()), environ=dict(bottle.request.environ))
            user = Application.user_initialization_hook()
            host = self._host()
            return PipeFactory.get_pipe(request).process(controller(), app, request, user, host)

        super().route(path.rstrip("/"), ["GET", "POST"], wrapper)

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return super().__call__(e, h)


class Controller(metaclass=ABCMeta):

    default_action = "not_implemented"

    @staticmethod
    def not_implemented():
        raise NotImplementedError()

    def process(self, app: Application, request, user, host):
        domain_data = self.setup(app=app, request=request, user=user, host=host)
        try:
            return self.__getattribute__(request.get("action", self.__class__.default_action))(
                app=app, request=request, user=user, host=host, domain_data=domain_data
            )
        except AttributeError:
            raise NotImplementedError()

    @abstractmethod
    def setup(self, app, request, user, host):
        """ """


class Request(object):
    class RequiredArgumentIsMissing(Exception):
        """ Исключение, возникающие если не предоставлен какой-либо из требуемых приложением параметров запроса """
        pass

    class Types(object):
        """ Типы запросов """
        STATIC = 0
        AJAX = 1
        PJAX = 2
        JSON_RPC = 3

    def __init__(self, *args, **kwargs):
        self._request = {}
        self.environ = kwargs.get("environ", {})

        for data in args:
            self.update(data)

    def get(self, key, default=None):
        """
        Возвращает значение параметра запроса по его имени
        @param key: Требуемый параметр
        @param default: Значение, используемое поумолчанию, если значения для key не предоставлено
        """
        if key in self._request.keys():
            return self._request.get(key)
        elif default is not None:
            return default
        else:
            raise Request.RequiredArgumentIsMissing("required argument '%s' is missing in your query" % key)

    def set(self, key, value):
        """
        Устанавливает значение параметра запроса по его имени
        @param key: Имя добавляемого параметра
        @param value: Значение добавляемого параметра
        """
        self._request.update({key: value})

    def update(self, other: dict):
        """
        Обновляет запрос данными из словаря
        """
        if isinstance(other, dict):
            self._request.update(other)
        else:
            raise TypeError("request cannot be updated by value of class %s" % other.__class__.__name__)

    def type(self):
        """
        Определяет тип запроса
        """
        if self.get("q", False):
            return self.Types.JSON_RPC
        elif self.environ.get("HTTP_X_REQUESTED_WITH", "").lower() == 'xmlhttprequest':
            if self.environ.get("HTTP_X_PJAX"):
                return self.Types.PJAX
            else:
                return self.Types.AJAX
        else:
            return self.Types.STATIC


class RequestPipe(metaclass=ABCMeta):
    def process(self, controller, app: Application, request, user, host):
        return self.__class__.converter(lambda: controller.process(app, request, user, host))

    @staticmethod
    def converter(cb):
        """
            Конвертор
        """
        # noinspection PyBroadException
        try:
            return cb()
        except:
            return ""


class StaticPipe(RequestPipe):
    pass


class AjaxPipe(RequestPipe):
    pass


class PjaxPipe(RequestPipe):
    pass


class JsonRpcPipe(RequestPipe):
    """
    Реализация обработки JSON RPC запроса
    """
    def process(self, controller: Controller, app: Application, request, user, host):
        def wrapper(method, params):
            if isinstance(params, dict):
                request.update(params)

            request.set('params', params)
            request.set('action', method)
            return controller.process(app, request, user, host)

        try:
            json = simplejson.loads(request.get("q"))

            if isinstance(json, dict):
                json = [json]

            if isinstance(json, list) and len(json):
                response = lambda: list(filter(None, [JsonRpcPipe.response(j, wrapper) for j in json]))
            else:
                response = JsonRpcPipe.invalid_request
        except simplejson.JSONDecodeError:
            response = JsonRpcPipe.parse_error

        return JsonRpcPipe.converter(response)

    @staticmethod
    def converter(cb):
        result = cb()
        if result:
            if len(result) == 1:
                return simplejson.dumps(result.pop())
            else:
                return simplejson.dumps(result)

        return ''

    @staticmethod
    def parse_error():
        """
        Invalid JSON was received by the server
        An error occurred on the server while parsing the JSON text
        """
        return {'jsonrpc': '2.0', 'error': {'code': -32700, 'message': 'Parse error'}, 'id': None}

    @staticmethod
    def invalid_request(id=None):
        """ The JSON sent is not a valid Request object """
        return {'jsonrpc': '2.0', 'error': {'code': -32600, 'message': 'Invalid Request'}, 'id': id}

    @staticmethod
    def method_not_found(id=None):
        """ The method does not exist / is not available """
        return {'jsonrpc': '2.0', 'error': {'code': -32601, 'message': 'Method not found'}, 'id': id}

    @staticmethod
    def invalid_params(id=None):
        """ Invalid method parameter(s) """
        return {'jsonrpc': '2.0', 'error': {'code': -32602, 'message': 'Invalid params'}, 'id': id}

    @staticmethod
    def internal_error(id=None):
        """ Internal JSON-RPC error """
        return {'jsonrpc': '2.0', 'error': {'code': -32603, 'message': 'Internal error'}, 'id': id}

    @staticmethod
    def server_error(code, id=None):
        """ Reserved for implementation-defined server-errors. Code MUST BE in range from 0 to 99 """
        return {'jsonrpc': '2.0', 'error': {'code': -32000 - code, 'message': 'Server error'}, 'id': id}

    @staticmethod
    def success(result, id):
        """ Ответ на успешно выполненный запрос """
        return {'jsonrpc': '2.0', 'result': result, 'id': id}

    @staticmethod
    def response(json, cb):
        """ Отвечает на один RPC запрос """
        if not isinstance(json, dict) or len(json) == 0:
            return JsonRpcPipe.invalid_request()

        _id, params, method, version = json.get('id'), json.get('params', []), json.get('method'), json.get('jsonrpc')

        if not version:
            return JsonRpcPipe.invalid_request(_id) if _id else None

        if not isinstance(method, str):
            return JsonRpcPipe.invalid_request(_id) if _id else None

        if not isinstance(params, (dict, list)):
            return JsonRpcPipe.invalid_params(_id) if _id else None

        # noinspection PyBroadException
        try:
            return JsonRpcPipe.success(cb(method, params), _id) if _id else None
        except Request.RequiredArgumentIsMissing:
            return JsonRpcPipe.invalid_params(_id) if _id else None
        except NotImplementedError:
            return JsonRpcPipe.method_not_found(_id) if _id else None
        except:
            return JsonRpcPipe.server_error(0, _id) if _id else None


class PipeFactory(object):
    @staticmethod
    def get_pipe(request: Request):
        if request.type() == Request.Types.PJAX:
            return PjaxPipe()
        elif request.type() == Request.Types.AJAX:
            return AjaxPipe()
        elif request.type() == Request.Types.JSON_RPC:
            return JsonRpcPipe()
        else:
            return StaticPipe()


