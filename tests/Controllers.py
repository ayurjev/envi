from envi import Controller


class BaseController(Controller):
    default_action = "index"

    def setup(self, **kwargs):
        return 1

    @staticmethod
    def index(app, request, user, host, domain_data):
        return app, request, user, host, domain_data


class UsersController(Controller):
    """ Пример контроллера действий над пользователями """
    default_action = "show"

    def setup(self, **kwargs):
        pass

    @staticmethod
    def show(**kwargs):
        return "show users"


class RequestController(Controller):
    def setup(self, **kwargs):
        pass

    @staticmethod
    def get_arg(request, **kwargs):
        return request.get('arg')

    @staticmethod
    def get_file(request, **kwargs):
        request.get('arg').save("/tmp/test.txt", True)
        with open('/tmp/test.txt') as f:
            return f.readlines()


