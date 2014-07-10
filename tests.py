import unittest
import json
from webtest import TestApp
from envi import Application, Controller, ProxyController, Request, template, ControllerMethodResponseWithTemplate


class TestProxyController(ProxyController):
    """ Тестовый проксиурющий контроллер """
    @staticmethod
    def factory_method(app, request, user, host):
        if request.get("option") == "1":
            return TestController
        else:
            return TestController2


# noinspection PyUnusedLocal
class TestController(Controller):
    """ Тестовый контроллер """
    default_action = "return_str"

    def setup(self, **kwargs):
        return {}

    @staticmethod
    def return_dict(**kwargs):
        return {"a": 1, "b": 2}

    @staticmethod
    def return_exception(**kwargs):
        raise Exception("Error!!!")

    @staticmethod
    def return_str(**kwargs):
        return "Hello"

    @staticmethod
    def return_bool(**kwargs):
        return True

    @staticmethod
    @template("template_name_here")
    def return_html_by_templating(request, **kwargs):
        request.response.add_header("HTTP_X_TEST", 111)
        return {"a": 1, "b": 2}


# noinspection PyUnusedLocal
class TestController2(Controller):
    """ Второй тестовый контроллер """
    @staticmethod
    def return_str(**kwargs):
        return "Goodbye"


# noinspection PyUnusedLocal
class ReflectionController(Controller):
    """ Тестовый контроллер, отражающий обратно полученные параметры запроса """

    @staticmethod
    def return_arg(request, **kwargs):
        return request.get('arg')

    @staticmethod
    def return_file(request, **kwargs):
        return request.get('arg').file.read()

    @staticmethod
    def return_user(user, **kwargs):
        return "User Is None" if not user else "User Is Not None"


class FirstException(Exception):
    def __init__(self):
        super().__init__("Первое исключение")


class SecondException(Exception):
    def __init__(self):
        super().__init__("Второе исключение")


class ThirdException(Exception):
    def __init__(self):
        super().__init__("Третье исключение")


class ControllerTestsFixture(unittest.TestCase):
    def setUp(self):
        self.app = Application(catchall=False)
        self.app.route("/", TestController)
        self.app.route("/<action>/", TestController)
        self.app.route("/options/", TestProxyController)
        self.app.route("/reflection/<action>/", ReflectionController)
        self.app.route("/reflection/<action>/<arg>/", ReflectionController)

        self.test_app = TestApp(self.app)

    def get_query(self, url, data=None):
        return self.test_app.get(url, data if data else None).body.decode("utf-8")

    def post_query(self, url, data=None):
        return self.test_app.post(url, data if data else {}, xhr=True).body.decode()

    def get_headers_from_get_query(self, url):
        return self.test_app.get(url).headers


class ControllerTests(ControllerTestsFixture):
    """ Тесты envi-контроллера """

    def test_default_action_routing(self):
        """ Если запрос приходит без указания action,
        то запрос обслуживается методом контроллера, указанным в свойстве default_action
        """
        self.assertEqual("Hello", self.get_query("/"))

    def test_action_routing_get_method(self):
        """ Контроллер корректно проксирует GET-запрос на метод, соответствующий переданному параметру action
        и корректно форматирует ответ в соответствии с типом возвращаемого значения """

        # Запрос на контроллер, возвращающий словарь:
        self.assertDictEqual(json.loads('''{"a": 1, "b": 2}'''), json.loads(self.get_query("/return_dict/")))

        # Запрос на контроллер, возвращающий шаблонизируемую страницу (при этом шаблонизация не установлена)
        self.assertCountEqual(
            '''template_name_here + {"a": 1, "b": 2}''''',
            self.get_query("/return_html_by_templating/")
        )

        # Запрос на контроллер, возвращающий строковое значение:
        self.assertEqual("Hello", self.get_query("/return_str/"))

        # Запрос на контроллер, возвращающий булево значение:
        self.assertEqual("True", self.get_query("/return_bool/"))

        # Запрос на контроллер, порождающий исключение:
        self.assertCountEqual(
            '''error_template + {"error": {"type": "<class 'Exception'>", "message": "Error!!!"}}''''',
            self.get_query("/return_exception/")
        )

    def test_action_routing_post_method(self):
        """ Контроллер корректно проксирует POST-запрос на метод, соответствующий переданному параметру action
        и корректно форматирует ответ в соответствии с типом возвращаемого значения """

        # Запрос на контроллер, возвращающий словарь:
        self.assertDictEqual(json.loads('''{"a": 1, "b": 2}'''), json.loads(self.post_query("/return_dict/")))

        # Запрос на контроллер, возвращающий шаблонизируемую страницу (при этом шаблонизация не установлена)
        self.assertCountEqual(
            json.loads('''{"a": 1, "b": 2}'''),
            json.loads(self.post_query("/return_html_by_templating/"))
        )

        # Запрос на контроллер, возвращающий строковое значение:
        self.assertEqual("Hello", self.post_query("/return_str/"))

        # Запрос на контроллер, порождающий исключение:
        self.assertCountEqual(
            json.loads('''{"error": {"type": "<class 'Exception'>", "message": "Error!!!"}}'''),
            json.loads(self.post_query("/return_exception/"))
        )

    def test_headers(self):
        """ Контроллер корректно возвращает все хедеры переданные сервером в ответ на запрос """
        headers = self.get_headers_from_get_query("/return_html_by_templating/")
        self.assertEqual("111", headers.get('http-x-test'))


class ProxyControllerTests(ControllerTestsFixture):
    """ Тесты проксирующего контроллера """
    def test_proxy(self):
        """ Если роутинг указывает на проксирующий контроллер, то запрос корректно перенаправляется """
        self.assertEqual("Hello", self.post_query("/options/", {"action": "return_str", "option": 1}))
        self.assertEqual("Goodbye", self.post_query("/options/", {"action": "return_str", "option": 2}))


class RequestTests(unittest.TestCase):
    def setUp(self):
        """ Каждый тест получает пустой объект запроса """
        self.request = Request()

    def test_getter(self):
        """ Запрос инициализируется любым количеством словарей """
        request = Request({'a': 1}, {'b': 2}, {'c': 3}, {'d': 4})
        self.assertEqual(1, request.get('a'))
        self.assertEqual(2, request.get('b'))
        self.assertEqual(3, request.get('c'))
        self.assertEqual(4, request.get('d'))

    def test_getter_type_casting(self):
        """ Автоматическое приведение аргументов к нужному типу """
        request = Request({'b': '2'})
        self.assertEqual('2', request.get('b'))
        self.assertEqual(2, request.get('b', cast_type=int))

    def test_getter_type_casting_exception(self):
        """ Выброс исключения при невозможности приведения аргументов к нужному типу """
        request = Request({'a': '1abc'})
        self.assertRaises(Request.ArgumentTypeError, request.get, 'a', cast_type=int)
        self.assertEqual('1abc', request.get('a'))

    def test_getter_default(self):
        request = Request({'a': 1}, {'b': 2}, {'c': 3}, {'d': 4})
        self.assertRaises(Request.RequiredArgumentIsMissing, request.get, 'x')
        self.assertEqual("xxx", request.get('x', "xxx"))
        self.assertEqual("xxx", request.get('x', default="xxx"))
        self.assertEqual(None, request.get('x', None))
        self.assertEqual(None, request.get('x', default=None))

    def test_setter(self):
        """ Сеттер добавляет в запрос новый аргумент """
        self.request.set('argument', True)
        self.assertEqual(True, self.request.get('argument'))

    def test_update_from_dictionary(self):
        """ Запрос можно обновить данными из словаря """
        self.request.update({'a': 1, 'b': 2})
        self.assertEqual(1, self.request.get('a'))
        self.assertEqual(2, self.request.get('b'))

    def test_update_from_non_dictionary(self):
        """ Попытка обновить запрос не из словаря вызывает исключение """
        self.assertRaises(TypeError, self.request.update, 1)
        self.assertRaises(TypeError, self.request.update, [])

    def test_missing_argument_with_default_value(self):
        """ Запрос отсутствующего аргумента с указанием дефолтного значения возвращает переданное дефолтное значение """
        self.assertEqual(2, self.request.get('missing_argument_with_default_value', 2))

    def test_missing_argument(self):
        """ Запрос отсутствующего аргумента без указания дефолтного значения вызывает исключение """
        self.assertRaises(Request.RequiredArgumentIsMissing, self.request.get, 'missing_argument')

    def test_override(self):
        """ Из нескольких значений аргумента в запросе сохранится последнее переданное """
        request = Request({'prop': 1}, {'prop': 2})
        self.assertEqual(2, request.get('prop'))

        request.set('prop', 3)
        self.assertEqual(3, request.get('prop'))

        request.update({'prop': 4})
        self.assertEqual(4, request.get('prop'))

    def test_ajax_type_detection(self):
        """ Ajax запрос определяется по заголовку HTTP_X_REQUESTED_WITH """
        request = Request(environ={"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(Request.Types.AJAX, request.type())

    def test_pjax_type_detection(self):
        """ Pjax запрос определяется по двум заголовкам HTTP_X_REQUESTED_WITH и HTTP_X_PJAX """
        request = Request(environ={"HTTP_X_PJAX": True, "HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(Request.Types.PJAX, request.type())

    def test_json_rpc_type_detection(self):
        """ JsonRPC запрос определяется по наличию аргумента q в запросе и только по нему одному """
        request = Request({"q": "{}"})
        self.assertEqual(Request.Types.JSON_RPC, request.type())

        request = Request({"q": "{}"}, environ={"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(Request.Types.JSON_RPC, request.type())

    def test_static_type_detection(self):
        """ Любой запрос не являющийся Ajax, Pjax, Json_RPC является STATIC """
        request = Request()
        self.assertEqual(Request.Types.STATIC, request.type())


class EnvironmentReflectionTests(ControllerTestsFixture):
    """ Тесты отражения переданной в контроллер информации """
    def test_request_get_arguments(self):
        """ Request содержит в себе GET параметры """
        self.assertEqual("123", self.get_query("/reflection/return_arg/", {'arg': '123'}))

    def test_request_post_arguments(self):
        """ Request содержит в себе POST параметры """
        self.assertEqual("123", self.post_query("/reflection/return_arg/", {'arg': '123'}))

    def test_request_files_arguments(self):
        """ Request содержит в себе FILES """
        self.assertEqual(
            b"FILE CONTENT",
            self.test_app.post(
                "/reflection/return_file/",
                upload_files=[('arg', 'text/plain', b'FILE CONTENT')], xhr=True
            ).body
        )

    def test_multibyte_request_params(self):
        """ Контроллер умеет принимать параметры в multi-byte кодировке """
        self.assertEqual(
            "параметр".encode(),
            self.test_app.get(
                None, extra_environ={'PATH_INFO': "/reflection/return_arg/параметр/".encode().decode("iso-8859-1")}
            ).body
        )

    def test_user_initialization(self):
        """ Если в приложении Apllication не переопределен user_initialization_hook,
        то в контроллер приходит user = None, иначе - в соответствии с переопределением """
        self.assertEqual("User Is None", self.post_query("/reflection/return_user/"))
        self.app.user_initialization_hook = lambda r: "SomeUser"
        self.assertEqual("User Is Not None", self.post_query("/reflection/return_user/"))

    def test_custom_ajax_error_format(self):
        """ Для приложения можно переопределить формат возвращения исключений. возникающих при ajax-запросе """
        # Дефолтная реализация:
        self.assertCountEqual(
            json.loads('''{"error": {"type": "<class 'Exception'>", "message": "Error!!!"}}'''),
            json.loads(self.post_query("/return_exception/"))
        )

        self.app.ajax_output_converter = lambda r: {"ошибка": {"тип": "", "сообщение": "Ахтунг!!!"}}

        # Переопределенная реализация:
        self.assertCountEqual(
            json.loads('''{"ошибка": {"тип": "", "сообщение": "Ахтунг!!!"}}'''),
            json.loads(self.post_query("/return_exception/"))
        )

    def test_custom_ajax_success_response_format(self):
        """ Для приложения можно переопределить формат успешных ответов на ajax-запросы """
        # Дефолтная реализация:
        self.assertCountEqual(
            json.loads('''{"a": "1", "b": "2"}'''),
            json.loads(self.post_query("/return_dict/"))
        )

        self.app.ajax_output_converter = lambda res: {"result": res}

        # Переопределенная реализация:
        self.assertCountEqual(
            json.loads('''{"result": {"a": "1", "b": "2"}}'''),
            json.loads(self.post_query("/return_dict/"))
        )

    def test_custom_get_error_format(self):
        """ Для приложения можно переопределить формат возвращения исключений, возникающих при статической загрузке """
        # Дефолтная реализация:
        self.assertCountEqual(
            '''error_template + {"error": {"type": "<class 'Exception'>", "message": "Error!!!"}}''',
            self.get_query("/return_exception/")
        )

        self.app.static_output_converter = lambda res: "%s + %s" % (json.dumps(res.data), res.template)

        # Переопределенная реализация:
        self.assertCountEqual(
            '''{"error": {"type": "<class 'Exception'>", "message": "Error!!!"}} + error_template''',
            self.get_query("/return_exception/")
        )

    def test_custom_get_successful_page_format(self):
        """ Для приложения можно переопределить формат возвращения успешно сгенерированных статчиеских страниц,
        то есть можно назначить пользовательскую шаблонизацию """
        # Дефолтная реализация:
        self.assertCountEqual(
            '''template_name_here + {"b": 2, "a": 1}''',
            self.get_query("/return_html_by_templating/")
        )

        self.app.static_output_converter = lambda res: "%s + %s" % (json.dumps(res.data), res.template)

        # Переопределенная реализация:
        self.assertCountEqual(
            '''{"b": 2, "a": 1} + template_name_here''',
            self.get_query("/return_html_by_templating/")
        )


class TestTemplateDecorator(unittest.TestCase):

    @staticmethod
    def controller_method():
        return {"a": 1, "b": 2, "c": 3}

    @staticmethod
    def controller_method_error():
        raise SecondException()

    def test_normal_templating(self):
        """ Имя шаблона возвращается вместе с результатами выполнения декорируемого метода контроллера """
        @template("normal_template")
        def controller_method_with_normal_templating() -> ControllerMethodResponseWithTemplate:
            return TestTemplateDecorator.controller_method()

        result = controller_method_with_normal_templating()
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertEqual({"a": 1, "b": 2, "c": 3}, result.data)
        self.assertEqual("normal_template", result.template)

    def test_templating_with_conditions(self):
        """ При декорировании можно указывать условия выбора того или иного шаблона

        Решение будет приниматься на основании результата выполнения декорируемого метода контроллера
        """
        @template("normal_template")
        @template("first_template", if_true=lambda res: res["a"] == 1)
        @template("second_template", if_true=lambda res: res["a"] == 2)
        def controller_method__wrapper(a) -> ControllerMethodResponseWithTemplate:
            controller_result = TestTemplateDecorator.controller_method()
            controller_result.update({"a": a})
            return controller_result

        # Выполняется первое условие (средний декоратор)
        result = controller_method__wrapper(1)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"a": 1, "b": 2, "c": 3}, result.data)
        self.assertEqual("first_template", result.template)

        # Выполняется второе условие (последний декоратор)
        result = controller_method__wrapper(2)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"a": 2, "b": 2, "c": 3}, result.data)
        self.assertEqual("second_template", result.template)

        # Ни одно из условий не выполняется - используется первый декоратор
        result = controller_method__wrapper(3)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"a": 3, "b": 2, "c": 3}, result.data)
        self.assertEqual("normal_template", result.template)

    def test_templating_with_error_handling(self):
        """ При декорировании можно указывать тип вероятного исключения

        и какой шаблон для данного исключения необходимо использовать
        """
        @template("normal_template")
        @template("first_template", if_exc=FirstException)
        @template("second_template", if_exc=SecondException)
        def controller_method__wrapper(exc_type=None) -> ControllerMethodResponseWithTemplate:
            if exc_type:
                raise exc_type()
            return TestTemplateDecorator.controller_method()

        # Исключения не возникло - используем первый декоратор
        result = controller_method__wrapper()
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"a": 1, "b": 2, "c": 3}, result.data)
        self.assertEqual("normal_template", result.template)

        # Исключение FirstException - второй декоратор
        result = controller_method__wrapper(FirstException)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual(
            {"name": "FirstException", "message": "Первое исключение"}, result.data
        )
        self.assertEqual("first_template", result.template)

        # Исключение SecondException - третий декоратор
        result = controller_method__wrapper(SecondException)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual(
            {"name": "SecondException", "message": "Второе исключение"}, result.data
        )
        self.assertEqual("second_template", result.template)

        # Исключения, неопределенные при декорировании - Исключение продолжает всплывать вверх по стеку
        self.assertRaises(Exception, controller_method__wrapper, Exception)
        self.assertRaises(ThirdException, controller_method__wrapper, ThirdException)

    def test_all_options(self):
        """
        При декорировании можно комбинировать условия выбора шаблона на основании результатов
        выполнения декорированного метода контроллера
        и условия выбора шаблона по типу вероятного исключения

        Порядок наложения декораторов в таком случае должен быть следующим:

        Дефолтный шаблон
        [Условие1]
        [Условие2]
        [...]
        [Базовый тип исключений]
        [Субтип исключений1]
        [Субтип исключений2]
        [...]

        """
        @template("normal_template")
        @template("first_template", if_true=lambda res: res["a"] == 1)
        @template("second_template", if_true=lambda res: res["a"] == 2)
        @template("first_exc_template", if_exc=FirstException)
        @template("second_exc_template", if_exc=SecondException)
        def controller_method__wrapper(a, exc_type=None) -> ControllerMethodResponseWithTemplate:
            if exc_type:
                raise exc_type()
            controller_result = TestTemplateDecorator.controller_method()
            controller_result.update({"a": a})
            return controller_result

        # Исключений нет, первое условие - второй декоратор
        result = controller_method__wrapper(1)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"a": 1, "b": 2, "c": 3}, result.data)
        self.assertEqual("first_template", result.template)

        # Исключений нет, второе условие - третий декоратор
        result = controller_method__wrapper(2)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"a": 2, "b": 2, "c": 3}, result.data)
        self.assertEqual("second_template", result.template)

        # Исключений нет, условия не выполняются - первый, дефолтный, декоратор
        result = controller_method__wrapper(3)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"a": 3, "b": 2, "c": 3}, result.data)
        self.assertEqual("normal_template", result.template)

        # Первое исключение, условия не важны - четвертый декоратор
        result = controller_method__wrapper(1, FirstException)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"name": "FirstException", "message": "Первое исключение"}, result.data)
        self.assertEqual("first_exc_template", result.template)

        # Первое исключение, условия не важны - четвертый декоратор
        result = controller_method__wrapper(2, FirstException)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"name": "FirstException", "message": "Первое исключение"}, result.data)
        self.assertEqual("first_exc_template", result.template)

        # Второе исключение, условия не важны - пятый декоратор
        result = controller_method__wrapper(1, SecondException)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"name": "SecondException", "message": "Второе исключение"}, result.data)
        self.assertEqual("second_exc_template", result.template)

        # Второе исключение, условия не важны - пятый декоратор
        result = controller_method__wrapper(2, SecondException)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"name": "SecondException", "message": "Второе исключение"}, result.data)
        self.assertEqual("second_exc_template", result.template)

        # Первое исключение, условия не важны - четвертый декоратор
        result = controller_method__wrapper(3, FirstException)
        self.assertTrue(isinstance(result, ControllerMethodResponseWithTemplate))
        self.assertCountEqual({"name": "FirstException", "message": "Первое исключение"}, result.data)
        self.assertEqual("first_exc_template", result.template)

        # Неотслеживаемое декораторами исключение, условия не важны - исключение продолжает всплывать вверх по стеку
        self.assertRaises(Exception, controller_method__wrapper, 1, Exception)
        self.assertRaises(Exception, controller_method__wrapper, 3, Exception)
        self.assertRaises(ThirdException, controller_method__wrapper, 1, ThirdException)
        self.assertRaises(ThirdException, controller_method__wrapper, 3, ThirdException)


if __name__ == "__main__":
    unittest.main()