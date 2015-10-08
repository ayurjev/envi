import re
import json
import time as profiler_time
import traceback
from io import BytesIO
import bottle
from abc import ABCMeta, abstractmethod
from datetime import datetime, date, time


""" 16 Mb """
bottle.BaseRequest.MEMFILE_MAX = 16 * 1024 * 1024


class ControllerMethodResponseWithTemplate(object):
    """ Класс для оформления результатов работы декоратора template """

    def __init__(self, data, template_name):
        self.data = data
        self.template = template_name

    def __str__(self):
        return json.dumps(self.data, default=json_dumps_handler) if isinstance(self.data, (list, dict)) else str(
            self.data)


class Profiler(object):
    def __init__(self):
        self._startTime = 0

    def __enter__(self):
        self._startTime = profiler_time.time()
        return self

    def __exit__(self, etype, value, traceback):
        pass

    def get_amount(self):
        return float(profiler_time.time() - self._startTime)


class Application(bottle.Bottle):
    ignored_exceptions = []

    def __init__(self):
        super().__init__(catchall=False)

    @classmethod
    def log(cls, err: Exception):
        ignored_exceptions = tuple([Request.RequiredArgumentIsMissing] + cls.ignored_exceptions)
        if not isinstance(err, ignored_exceptions):
            traceback.print_exc()

    @classmethod
    def performance_report(cls, user, request, result, amount):
        pass

    # noinspection PyMethodMayBeStatic
    def user_initialization_hook(self, request):
        """ Функция для инициализации пользователя приложения """
        return None

    # noinspection PyMethodMayBeStatic
    def ajax_output_converter(self, result) -> dict:
        """ Функция для конвертации ответов при ajax запросах
        Здесь можно настроить формат положительных и отрицательных результатов ajax-запросов
        :param result: Экземпляр исключения (Exception) или Словарь с данными (dict)
        """
        if isinstance(result, Exception):
            return {"error": {"type": str(type(result)), "message": str(result)}}
        else:
            return result

    # noinspection PyMethodMayBeStatic
    def static_output_converter(self, result: ControllerMethodResponseWithTemplate) -> str:
        """ Функция для конвертации ответов при статических загрузках страницы
        Переопределить для подключения кастомной шаблонизации
        :param result: Ответ в формате ControllerMethodResponseWithTemplate
        """
        return "%s + %s" % (result.template, json.dumps(result.data, default=json_dumps_handler))

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
            try:
                get_decoded = dict(bottle.request.GET.decode())
                post_decoded = dict(bottle.request.POST.decode())
            except UnicodeDecodeError as err:
                response = self.ajax_output_converter(Exception("Invalid HTTP request encoding. Must be 'ISO-8859-1'."))
                self.log(err)
                return response

            try:
                post_json = json.loads(post_decoded.get("json", get_decoded.get("json", "{}")),
                                       object_hook=json_loads_handler)
            except:
                post_json = {}

            request = Request(
                dict(bottle.request.cookies),
                kwargs, get_decoded, post_decoded,
                {'json': post_json} if isinstance(post_json, list) else post_json,
                environ=dict(bottle.request.environ))

            if action:
                request.set("action", action)

            with Profiler() as p:
                # noinspection PyNoneFunctionAssignment
                try:
                    user = self.user_initialization_hook(request)
                except Exception as err:
                    if not isinstance(err, bottle.HTTPResponse):
                        self.log(err)
                        response = self.ajax_output_converter(err)
                        return response
                    else:
                        raise err
                host = self._host()
                pipe = JsonRpcRequestPipe() if request.type() == Request.Types.JSON_RPC else RequestPipe()
                result = pipe.process(controller(), app, request, user, host)
                self.performance_report(user, request, result, p.get_amount())
                if isinstance(result, (bytes, bytearray)) or (type(result) is bottle.HTTPResponse):
                    return result
                return json.dumps(result, default=json_dumps_handler) if isinstance(result, (list, dict)) else str(
                    result)

        if path != '/':
            path = path.rstrip("/")

        super().route(path, ["GET", "POST"], wrapper)

    def route_static(self, root, **kwargs):
        """
        Роутинг статики
        :param root: директория с статикой
        """

        class StaticController(Controller):
            default_action = 'static'

            def static(self, request, **kwargs):
                search = r'^(.*)\.(v[0-9]+)?\.(css|js)$'
                replace = r'\1.\3'
                path = request.get('path')
                r = re.compile(search)
                path = r.sub(replace, path)
                return bottle.static_file(path, root)

        self.route("/<path:re:.*\..*>", StaticController)

    @staticmethod
    def redirect(path, code=None):
        bottle.redirect(path, code)

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        try:
            return super().__call__(e, h)
        except SystemExit:
            # Уходим молча.
            # Заголовки не отправляем.
            return []


class Controller(metaclass=ABCMeta):
    error_template = "error_template"
    default_action = "not_implemented"

    @staticmethod
    def not_implemented(**kwargs):
        raise NotImplementedError()

    def process(self, app: Application, request, user, host):
        error_response2 = lambda error_data: ControllerMethodResponseWithTemplate(error_data, self.error_template)
        request.set("error_response2", error_response2)

        domain_data = self.setup(app=app, request=request, user=user, host=host)

        error_response = lambda error_data: self.apply_to_each_response(
            response=ControllerMethodResponseWithTemplate(error_data, self.error_template),
            app=app, request=request, user=user, host=host, **domain_data)

        request.set("error_response", error_response)

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

    # noinspection PyMethodMayBeStatic
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


class WebSocketController(Controller):
    default_action = "connect"

    def open(self, app, request, user, host):
        """ Открытие сокета """

    def close(self, app, request, user, host):
        """ Закрытие сокета """

    def tick(self, app, request, user, host):
        """ Получение сообщения с сокета """

    def connect(self, app, request, user, host):
        # noinspection PyUnresolvedReferences
        import uwsgi
        import json

        uwsgi.websocket_handshake()

        self.open(app=app, request=request, user=user, host=host)
        try:
            while True:
                try:
                    msg = uwsgi.websocket_recv()
                except OSError:
                    raise SystemExit()

                msg = msg.decode()
                msg = json.loads(msg)
                if "action" in msg:
                    ws_request = Request(msg, environ=request.environ)
                    pipe = RequestPipe()
                    result = pipe.process(self, app, ws_request, user, host)
                    if isinstance(result, dict):
                        result.update({"ws": {"event": msg["action"]}})
                    if isinstance(result, (bytes, bytearray)):
                        uwsgi.websocket_send(result)
                    else:
                        uwsgi.websocket_send(
                            json.dumps(result, default=json_dumps_handler)
                            if isinstance(result, (list, dict)) else str(result)
                        )
                    self.tick(app=app, request=ws_request, user=user, host=host)
        finally:
            self.close(app=app, request=request, user=user, host=host)


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

    def get(self, key, *args, **kwargs):
        """
        Возвращает значение параметра запроса по его имени
        @param key: Требуемый параметр
        @param default: Значение, используемое поумолчанию, если значения для key не предоставлено
        """

        default = args[0] if len(args) > 0 else kwargs.get("default")
        cast_type = args[1] if len(args) > 1 else kwargs.get("cast_type")

        if key in self._request.keys():
            value = self._request.get(key)
            try:
                return cast_type(value) if cast_type is not None else value
            except ValueError:
                raise Request.ArgumentTypeError("argument '%s' can't be casted to %s" % (key, cast_type))

        if "default" in kwargs or len(args) > 0:
            return default
        else:
            raise Request.RequiredArgumentIsMissing("required argument '%s' is missing in your query" % key)

    def get_file(self, key):
        b = BytesIO()
        self.get(key).save(b)
        return self.get(key).raw_filename, b.getvalue()

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
        elif self.environ.get("HTTP_UPGRADE") == "websocket":
            return self.Types.AJAX
        else:
            return self.Types.STATIC

    @property
    def method(self):
        return bottle.request.method

    @property
    def headers(self):
        return dict(bottle.request.headers)

    @property
    def url(self):
        return bottle.request.url

    @property
    def host(self):
        return bottle.request.environ.get("HTTP_HOST")

    @property
    def path(self):
        return bottle.request.path

    @property
    def cookies(self):
        return dict(bottle.request.cookies)

    @property
    def remote_ip(self):
        return bottle.request.remote_addr

    def items(self):
        return {
            key: value for key, value in self._request.items()
            if key not in ["error_response", "error_response2"]
        }.items()

    def __str__(self):
        return str(self.items())


class Response(object):
    add_header = bottle.response.add_header
    set_cookie = bottle.response.set_cookie
    delete_cookie = bottle.response.delete_cookie


class RequestPipe(metaclass=ABCMeta):
    def process(self, controller, app, request, user, host):
        try:
            result = controller.process(app, request, user, host)
            if isinstance(result, ControllerMethodResponseWithTemplate):
                result = app.static_output_converter(result) \
                    if request.type() == request.Types.STATIC else app.ajax_output_converter(result.data)
            elif request.type() != request.Types.STATIC:
                result = app.ajax_output_converter(result)
        except Exception as err:
            if isinstance(err, bottle.HTTPResponse):
                raise err
            else:
                app.log(err)
                try:
                    result = app.static_output_converter(request.get("error_response")(app.ajax_output_converter(err))) \
                        if request.type() == request.Types.STATIC else app.ajax_output_converter(err)
                except:
                    result = app.static_output_converter(request.get("error_response2")(app.ajax_output_converter(err))) \
                        if request.type() == request.Types.STATIC else app.ajax_output_converter(err)
        return result


class JsonRpcRequestPipe(RequestPipe):
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
            json_data = json.loads(request.get("q"))

            if isinstance(json_data, dict):
                json_data = [json_data]

            if isinstance(json_data, list) and len(json_data):
                response = lambda: list(filter(None, [JsonRpcRequestPipe.response(j, wrapper) for j in json_data]))
            else:
                response = JsonRpcRequestPipe.invalid_request
        except Exception:
            response = JsonRpcRequestPipe.parse_error

        request.response.add_header("Content-Type", "application/json")
        return JsonRpcRequestPipe.converter(response)

    @staticmethod
    def converter(cb):
        result = cb()
        if result:
            if isinstance(result, list) and len(result) == 1:
                return json.dumps(result.pop())
            else:
                return json.dumps(result)

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
            return JsonRpcRequestPipe.invalid_request()

        _id, params, method, version = json.get('id'), json.get('params', []), json.get('method'), json.get('jsonrpc')

        if not version:
            return JsonRpcRequestPipe.invalid_request(_id) if _id else None

        if not isinstance(method, str):
            return JsonRpcRequestPipe.invalid_request(_id) if _id else None

        if not isinstance(params, (dict, list)):
            return JsonRpcRequestPipe.invalid_params(_id) if _id else None

        # noinspection PyBroadException
        try:
            return JsonRpcRequestPipe.success(cb(method, params), _id) if _id else None
        except (Request.RequiredArgumentIsMissing, Request.ArgumentTypeError):
            return JsonRpcRequestPipe.invalid_params(_id) if _id else None
        except NotImplementedError:
            return JsonRpcRequestPipe.method_not_found(_id) if _id else None
        except:
            return JsonRpcRequestPipe.server_error(0, _id) if _id else None


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
                        {"name": re.search("'(.+)'", str(err.__class__)).group(1), "message": str(err)}, template_name
                    )
                # В противном случае продолжаем поднимать исключение вверх по стеку
                raise err

        return wrapped

    return decorator


def json_dumps_handler(obj):
    """ json dumps handler """
    if isinstance(obj, time):
        obj = datetime(1970, 1, 1, obj.hour, obj.minute, obj.second)
        return obj.ctime()
    if isinstance(obj, datetime) or isinstance(obj, date):
        return obj.ctime()
    return None


def json_loads_handler(data):
    """ json loads handler """
    for k, v in data.items():
        if isinstance(v, str) and re.search("\w\w\w[\s]+\w\w\w[\s]+\d[\d]*[\s]+\d\d:\d\d:\d\d[\s]+\d\d\d\d", v):
            try:
                data[k] = datetime.strptime(v, "%a %b %d %H:%M:%S %Y")
            except Exception as err:
                raise err
    return data
