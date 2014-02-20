from envi import Controller


class UsersController(Controller):
    """ Пример контроллера действий над пользователями """
    default_action = "show"

    def setup(self, **kwargs):
        return {}

    @staticmethod
    def show(**kwargs):
        return "show users"


