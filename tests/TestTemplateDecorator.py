
""" Тестирование работы декоратора для методов контроллера """

import unittest
from envi import template, ControllerMethodResponseWithTemplate


class FirstException(Exception):
    def __init__(self):
        super().__init__("Первое исключение")


class SecondException(Exception):
    def __init__(self):
        super().__init__("Второе исключение")


class ThirdException(Exception):
    def __init__(self):
        super().__init__("Третье исключение")


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
        def controller_method_with_normal_templating():
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
        def controller_method__wrapper(a):
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
        def controller_method__wrapper(exc_type=None):
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
        def controller_method__wrapper(a, exc_type=None):
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


if __name__ == '__main__':
    unittest.main()