from envi import Controller


class BaseController(Controller):
    default_action = "index"

    def setup(self, **kwargs):
        return {}

    @staticmethod
    def index(app, request, user, host, domain_data):
        return app, request, user, host, domain_data

    @staticmethod
    def subtract(request, **kwargs):
        if len(request.get("params")) < 2:
            raise request.RequiredArgumentIsMissing()

        return request.get("params")[0] - request.get("params")[1]

    @staticmethod
    def add(request, **kwargs):
        if len(request.get("params")) < 2:
            raise request.RequiredArgumentIsMissing()

        return sum(request.get("params"))

    @staticmethod
    def add_a_b(request, **kwargs):
        return request.get('a') + request.get('b')

    @staticmethod
    def divide(request, **kwargs):
        return request.get('dividend') / request.get('divisor')

    @staticmethod
    def dummy_action(**kwargs):
        pass


class UsersController(Controller):
    """ Пример контроллера действий над пользователями """
    default_action = "show"

    def setup(self, **kwargs):
        return {}

    @staticmethod
    def show(**kwargs):
        return "show users"


