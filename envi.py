import bottle
from abc import ABCMeta, abstractmethod
from pipes import PipeFactory


class Application(bottle.Bottle):
    @staticmethod
    def user_initialization_hook():
        """
            Функция для инициализации пользователя приложения
        """

    @staticmethod
    def static_converter(cb):
        """
            Конвертор ответа статических страниц
        """
        # noinspection PyBroadException
        try:
            return cb()
        except:
            return ""

    @staticmethod
    def ajax_converter(cb):
        """
            Конвертор ajax ответа
        """
        # noinspection PyBroadException
        try:
            return cb()
        except:
            return ""

    @staticmethod
    def pjax_converter(cb):
        """
            Конвертор pjax ответа
        """
        # noinspection PyBroadException
        try:
            return cb()
        except:
            return ""

    @staticmethod
    def jsonrpc_converter(cb):
        """
            Конвертор jsonrpc ответа
        """
        # noinspection PyBroadException
        try:
            return cb()
        except:
            return ""

    def set_user_initialization_hook(self, cb):
        self.__class__.user_initialization_hook = cb

    def set_static_pipe_output_converter(self, cb):
        self.__class__.static_converter = cb

    def set_ajax_pipe_output_converter(self, cb):
        self.__class__.ajax_converter = cb

    def set_pjax_pipe_output_converter(self, cb):
        self.__class__.pjax_converter = cb

    def set_jsonrpc_pipe_output_converter(self, cb):
        self.__class__.jsonrpc_converter = cb

    # noinspection PyMethodOverriding
    def route(self, path, controller):
        app = self

        def wrapper(*args, **kwargs):
            request = bottle.request
            user = app.user_initialization_hook()
            host = None

            pipe = PipeFactory.get_pipe(request)
            return pipe.process(controller(), app, request, user, host)

        super().route(path, ["GET", "POST"], wrapper)


class Controller(metaclass=ABCMeta):

    default_action = "not_implemented"

    @staticmethod
    def not_implemented():
        raise NotImplemented()

    def process(self, app, request, user, host):

        domain_data = self.setup(app, request, user, host)
        try:
            return self.__getattribute__(request.get("action", self.__class__.default_action))(
                app, request, user, host, domain_data
            )
        except AttributeError:
            raise NotImplemented()

    @abstractmethod
    def setup(self, app, request, user, host):
        """ """

