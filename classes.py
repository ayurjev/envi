import bottle
import simplejson
from abc import ABCMeta, abstractmethod


class Application(bottle.Bottle):
    @staticmethod
    def user_initialization_hook(application, request):
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
    def route(self, path, controller, action=None):
        app = self

        def wrapper(*args, **kwargs):
            get_decoded = dict(bottle.request.GET.decode())
            post_decoded = dict(bottle.request.POST.decode())

            try:
                post_json = simplejson.loads(post_decoded.get("json", "{}"))
            except simplejson.JSONDecodeError:
                post_json = {}

            request = Request(
                kwargs, get_decoded, post_decoded,
                {'json': post_json} if isinstance(post_json, list) else post_json,
                dict(bottle.request.cookies),
                environ=dict(bottle.request.environ))

            if action:
                request.set("action", action)

            user = Application.user_initialization_hook(app, request)
            host = self._host()
            return PipeFactory.get_pipe(request).process(controller(), app, request, user, host)

        if path != '/':
            path = path.rstrip("/")

        super().route(path, ["GET", "POST"], wrapper)

    @staticmethod
    def redirect(path, code=None):
        bottle.redirect(path, code)

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return super().__call__(e, h)


class Controller(metaclass=ABCMeta):

    default_action = "not_implemented"

    @staticmethod
    def not_implemented(**kwargs):
        raise NotImplementedError()

    def process(self, app: Application, request, user, host):
        domain_data = self.setup(app=app, request=request, user=user, host=host)
        try:
            cb = self.__getattribute__(request.get("action", self.__class__.default_action))
        except AttributeError:
            raise NotImplementedError()
        return self.apply_to_each_response(
            response=cb(app=app, request=request, user=user, host=host, **domain_data),
            app=app, request=request, user=user, host=host, **domain_data)

    def setup(self, app, request, user, host) -> dict:
        """ Можно переопределять в создаваемых контроллерах """
        return {}

    def apply_to_each_response(self, response, app, request, user, host, **kwargs):
        """ Можно переопределять в создаваемых контроллерах """
        return response


class ProxyController(Controller, metaclass=ABCMeta):
    """ Проксирующий контроллер """
    def setup(self, app, request, user, host):
        proxy_controller = self.factory_method(app, request, user, host)
        while issubclass(proxy_controller, ProxyController):
            proxy_controller = proxy_controller.factory_method(app, request, user, host)

        data = {"proxy_controller": proxy_controller, "action": request.get("action", proxy_controller.default_action)}
        request.set("action", "ret")
        return data

    @staticmethod
    def ret(proxy_controller, action, app, request, user, host):
        request.set("action", action)
        return proxy_controller().process(app, request, user, host)

    @staticmethod
    @abstractmethod
    def factory_method(app, request, user, host):
        """ Переопределить для возвращения корректного целевого контроллера
        :param app: приложение
        :param request: запрос
        :param user: пользователь
        :param host: хост
        :return: корректный целевой контроллер
        """


class Request(object):
    class RequiredArgumentIsMissing(Exception):
        """ Исключение, возникающие если не предоставлен какой-либо из требуемых приложением параметров запроса """
        pass

    class ArgumentTypeError(Exception):
        """ Исключение, возникающие при неудачной попытке приведения параметра запроса к желемому типу данных """
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
        self.response = Response()

        for data in args:
            self.update(data)

    def get(self, key, default=None, cast_type=None):
        """
        Возвращает значение параметра запроса по его имени
        @param key: Требуемый параметр
        @param default: Значение, используемое поумолчанию, если значения для key не предоставлено
        """
        if key in self._request.keys():
            value = self._request.get(key)
            try:
                return cast_type(value) if cast_type is not None else value
            except ValueError:
                raise Request.ArgumentTypeError("argument '%s' can't be casted to %s" % (key, cast_type))

        if default is not None:
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

    @property
    def url(self):
        return self.environ.get("PATH_INFO")


class Response(object):
    add_header = bottle.response.add_header
    set_cookie = bottle.response.set_cookie
    delete_cookie = bottle.response.delete_cookie


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

        request.response.add_header("Content-Type", "application/json")
        return JsonRpcPipe.converter(response)

    @staticmethod
    def converter(cb):
        result = cb()
        if result:
            if isinstance(result, list) and len(result) == 1:
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
        except (Request.RequiredArgumentIsMissing, Request.ArgumentTypeError):
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


class ControllerMethodResponseWithTemplate(object):
    """ Класс для оформления результатов работы декоратора template """
    def __init__(self, data, template_name):
        self.data = data
        self.template = template_name

    def __str__(self):
        return simplejson.dumps(self.data)



def template(template_name, if_true=None, if_exc=None):
    """
    Декоратор, предназначенный для декорирования методов класса Controller, позволяющий определять имя шаблона
    либо на основании проверки результатов выполнения декорируемого метода контроллера, либо на основании возникновения
    некоторых (определенных при декорировании) типов исключений

    """
    def decorator(func):
        def wrapped(*args, **kwargs):
            try:
                # Получаем данные контроллера или результат выполнения предыдущего в цепочке декоратора
                data = func(*args, **kwargs)
                # Если результат уже декорирован просто возвращаем его
                # (очевидно, один из нескольких декораторов уже успешно отработал)
                if isinstance(data, ControllerMethodResponseWithTemplate):
                    return data

                # Если передана функция проверки результатов выполнения метода контроллера,
                # то чтобы выбрать текуший template_name необходимо чтобы эта функция проверки вернула True
                if if_true:
                    if if_true(data):
                        return ControllerMethodResponseWithTemplate(data, template_name)
                    else:
                        # Если функция проверки не возвращает True,
                        # возвращаем только результат выполнения контроллера для других декораторов
                        return data
                elif if_exc:
                    # Если передано условия по типу исключения, но оно, очевидно, не возникло,
                    # возвращаем только результат выполнения контроллера для других декораторов
                    return data
                else:
                    # Если не передано ничего - значит это дефолтный декоратор.
                    # Декорируем и возвращаем в виде ControllerMethodResponseWithTemplate,
                    # тем самым прерывая цепочку декорирования
                    return ControllerMethodResponseWithTemplate(data, template_name)
            except Exception as err:
                # Если возникло исключение и при декорировании этот тип исключения был описан, то
                # # Декорируем и возвращаем в виде ControllerMethodResponseWithTemplate,
                # тем самым прерывая цепочку декорирования и всплытия исключения
                if if_exc and isinstance(err, if_exc):
                    return ControllerMethodResponseWithTemplate(
                        {"name": err.__class__.__name__, "message": str(err)}, template_name
                    )
                # В противном случае продолжаем поднимать исключение вверх по стеку
                raise err
        return wrapped
    return decorator
