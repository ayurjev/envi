import bottle
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
            "browser": bottle.request.environ.get("HTTP_USER_AGENT"),
            "host": bottle.request.environ.get("HTTP_HOST"),
            "content": {
                "type": bottle.request.environ.get("CONTENT_TYPE"),
                "length": bottle.request.environ.get("CONTENT_LENGTH"),
            }
        }

    # noinspection PyMethodOverriding
    def route(self, path, controller):
        app = self

        def wrapper(*args, **kwargs):
            request = Request(kwargs, dict(bottle.request.GET.decode()), dict(bottle.request.POST.decode()))
            user = Application.user_initialization_hook()
            host = self._host()
            return PipeFactory.get_pipe(request).process(controller(), app, request, user, host)

        super().route(path.rstrip("/"), ["GET", "POST"], wrapper)

    def __call__(self, e, h):
        e['PATH_INFO'] = e['PATH_INFO'].rstrip('/')
        return super().__call__(e, h)


class Request(object):
    class RequiredArgumentIsMissing(Exception):
        """ Исключение, возникающие если не предоставлен какой-либо из требуемых приложением параметров запроса """
        pass

    def __init__(self, *args):
        self._request = {}

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
    pass


class PipeFactory(object):
    @staticmethod
    def get_pipe(request):
        return AjaxPipe()


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

