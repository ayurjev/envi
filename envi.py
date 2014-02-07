import bottle
from abc import ABCMeta, abstractmethod
from pipes import PipeFactory, StaticPipe, AjaxPipe, PjaxPipe, JsonRpcPipe


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

    # noinspection PyMethodOverriding
    def route(self, path, controller):
        app = self

        def wrapper(*args, **kwargs):
            request = bottle.request
            user = Application.user_initialization_hook()
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

