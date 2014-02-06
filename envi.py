import bottle
from abc import ABCMeta, abstractmethod
from pipes import PipeFactory


class Application(bottle.Bottle):

    def __init__(self):
        super().__init__()
        self.user_initialization_hook = lambda: None
        self.static_converter = lambda cb: cb()
        self.ajax_converter = lambda cb: cb()
        self.pjax_converter = lambda cb: cb()
        self.jsonrpc_converter = lambda cb: cb()

    def set_user_initialization_hook(self, cb):
        self.user_initialization_hook = cb

    def set_static_pipe_output_converter(self, cb):
        self.static_converter = cb

    def set_ajax_pipe_output_converter(self, cb):
        self.ajax_converter = cb

    def set_pjax_pipe_output_converter(self, cb):
        self.pjax_converter = cb

    def set_jsonrpc_pipe_output_converter(self, cb):
        self.jsonrpc_converter = cb

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

