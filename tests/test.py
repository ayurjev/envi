import unittest
from envi.tests import TestRequest, TestEnviRequest, TestController, TestJsonRPCPipe, TestTemplateDecorator

suite = unittest.TestSuite(tests=(
    unittest.loader.findTestCases(TestRequest),
    unittest.loader.findTestCases(TestEnviRequest),
    unittest.loader.findTestCases(TestController),
    unittest.loader.findTestCases(TestJsonRPCPipe),
    unittest.loader.findTestCases(TestTemplateDecorator),
))

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite)
