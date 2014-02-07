from envi import Application
from abc import ABCMeta, abstractmethod


class RequestPipe(metaclass=ABCMeta):
    @abstractmethod
    def process(self, controller, app: Application, request, user, host):
        """ """


class StaticPipe(RequestPipe):
    def process(self, controller, app: Application, request, user, host):
        return app.static_converter(lambda: controller.process(app, request, user, host))


class AjaxPipe(RequestPipe):
    def process(self, controller, app: Application, request, user, host):
        return app.ajax_converter(lambda: controller.process(app, request, user, host))


class PjaxPipe(RequestPipe):
    def process(self, controller, app: Application, request, user, host):
        return app.pjax_converter(lambda: controller.process(app, request, user, host))


class JsonRpcPipe(RequestPipe):
    def process(self, controller, app: Application, request, user, host):
        return app.jsonrpc_converter(lambda: controller.process(app, request, user, host))


class PipeFactory(object):
    @staticmethod
    def get_pipe(request):
        return AjaxPipe()


