from envi import Controller

class BaseController(Controller):
    default_action = "index"

    def setup(self, app, request, user, host):
        return 1

    @staticmethod
    def index(app, request, user, host, domain_data):
        return app, request, user, host, domain_data


class UsersController(Controller):
    """ Пример контроллера действий над пользователями """
    default_action = "show"

    def setup(self, app, request, user, host):
        pass

    @staticmethod
    def show(app, request, user, host, data):
        return "show users"


class RequestController(Controller):
    def setup(self, app, request, user, host):
        pass

    @staticmethod
    def get_arg(app, request, user, host, data):
        return request.get('arg')

    @staticmethod
    def get_file(app, request, user, host, data):
        request.get('arg').save("/tmp/test.txt", True)
        with open('/tmp/test.txt') as f:
            return f.readlines()


