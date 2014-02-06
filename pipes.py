class RequestPipe(object):
    def process(self, controller, app, request, user, host):
        return controller.process(app, request, user, host)


class AjaxPipe(RequestPipe):
    def process(self, controller, app, request, user, host):
        return controller.process(app, request, user, host)


class PjaxPipe(RequestPipe):
    def process(self, controller, app, request, user, host):
        return controller.process(app, request, user, host)


class StaticPipe(RequestPipe):
    def process(self, controller, app, request, user, host):
        return app.static_converter(lambda: controller.process(app, request, user, host))


class JsonRpcPipe(RequestPipe):
    def process(self, controller, app, request, user, host):
        try:
            return controller.process(app, request, user, host)
        except:
            return ""


class PipeFactory(object):
    @staticmethod
    def get_pipe(request):
        return AjaxPipe()


