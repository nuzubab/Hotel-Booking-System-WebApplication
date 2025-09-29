from django.test.runner import DiscoverRunner

class CustomTestRunner(DiscoverRunner):
    def run_suite(self, suite, **kwargs):
        result = super().run_suite(suite, **kwargs)
        if result.wasSuccessful():
            print("\n====================")
            print("All tests passed successfully!")
            print("====================\n")
        return result
