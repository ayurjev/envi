"""
Контроллер уровня приложения

"""

import json
from z9.ThirdPartyLibs import bottle


class AppController(object):
    """ Основной контроллер уровня приложения """

    class NotFound(Exception):
        """ Исключение, сигнализирующее о 404 ошибке """
        pass

    @staticmethod
    def not_found():
        """ Возбуждает исключение 404 - Страница не найдена """
        raise AppController.NotFound()

    def __init__(self):
        self.user_initialization_hook = lambda: None

    def set_user_initialization_hook(self, cb):
        """
        Устанавливает коллбэк, возвращающий новый инстанс пользователя
        @param cb: Метод, возвращающий проинициализированный объект пользователя
        """
        self.user_initialization_hook = cb

    def produce(self, action=None, error_handler=None, template_name=None):
        """
        Возвращает декоратор, перенаправляющий поток выполнения на указанный контроллер,
        Выполняет его, обрабатывая ошибки в соответствии с error_handler и возвращает ответ в виде templateName
        @param action: Действие целевого контроллера
        @param error_handler: Обработчик ошибок
        @param template_name: Имя шаблона для шаблонизации результата
        """
        # noinspection PyDocstring
        def function_wrapper(route_handler):
            # noinspection PyDocstring
            def function_result_wrapper(**kwargs):
                request = Request(kwargs, dict(bottle.request.POST.decode()), bottle.request.files)
                user = self.user_initialization_hook()
                if action:
                    request.set("action", action)
                return error_handler(lambda: route_handler(request, user), self, request, user, template_name)
            return function_result_wrapper
        return function_wrapper


class Request(object):
    """ Класс для работы с http запросом """

    class RequiredArgumentIsMissing(Exception):
        """ Исключение, возникающие если не предоставлен какой-либо из требуемых приложением параметров запроса """
        pass

    class Types(object):
        """ Типизация запросов """
        STATIC = 0
        AJAX = 1
        PJAX = 2

    def __init__(self, url_data, post_data=None, files_data=None):
        self.request = {}

        # Данные из строки URL:
        for urlkey in url_data:
            self.request[urlkey] = url_data[urlkey].encode("iso-8859-1").decode("utf-8")

        # Данные из POST-массива
        if post_data is None:
            post_data = dict(bottle.request.POST.decode())
        for postkey in post_data:
            if postkey == "data":
                data_dict = json.loads(post_data[postkey])
                for datakey in data_dict:
                    self.request[datakey] = data_dict[datakey]
            else:
                self.request[postkey] = post_data[postkey]

        # Данные из массива FILES
        if files_data is None:
            files_data = bottle.request.files
        for fileupload in files_data:
            self.request[fileupload] = files_data.get(fileupload)

    def get(self, key, default=None):
        """
        Возвращает значение параметра запроса по его имени
        @param key: Требуемый параметр
        @param default: Значение, используемое поумолчанию, если значения для key не предоставлено
        """
        if key in self.request.keys():
            return self.request.get(key)
        elif default is not None:
            return default
        else:
            raise Request.RequiredArgumentIsMissing("required argument %s is missing in your query" % key)

    def set(self, key, value):
        """
        Устанавливает значение параметра запроса по его имени
        @param key: Имя добавляемого параметра
        @param value: Значение добавляемого параметра
        """
        self.request[key] = value

    @staticmethod
    def type():
        """ Возвращает тип http-запроса """
        if bottle.request.headers.get("X-Pjax") is not None:
            return Request.Types.PJAX
        elif len(bottle.request.POST) != 0:
            return Request.Types.AJAX
        else:
            return Request.Types.STATIC