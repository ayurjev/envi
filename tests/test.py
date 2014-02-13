import unittest
import tests.TestRequest
import tests.TestEnviRequest
import tests.TestController
import tests.TestJsonRPC



suite = unittest.TestSuite(tests=(
    unittest.loader.findTestCases(tests.TestRequest),
    unittest.loader.findTestCases(tests.TestEnviRequest),
    unittest.loader.findTestCases(tests.TestController),
    unittest.loader.findTestCases(tests.TestJsonRPC),
))

if __name__ == "__main__":
    unittest.TextTestRunner(verbosity=2).run(suite)
