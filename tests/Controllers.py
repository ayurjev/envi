from envi import Controller

class TestController(Controller):
    default_action = "index"

    def setup(self, app, request, user, host):
        return 1

    @staticmethod
    def index(app, request, user, host, domain_data):
        return app, request, user, host, domain_data


class UsersTestController(Controller):
    """ Пример контроллера действий над пользователями """
    default_action = "show"

    def setup(self, app, request, user, host):
        pass

    @staticmethod
    def show(app, request, user, host, data):
        return "show users"


class RequestTestController(Controller):
    def setup(self, app, request, user, host):
        pass

    @staticmethod
    def request_get(app, request, user, host, data):
        return request.get('get')

    @staticmethod
    def request_post(app, request, user, host, data):
        return request.get('post')

    @staticmethod
    def request_files(app, request, user, host, data):
        return request.get('files')


