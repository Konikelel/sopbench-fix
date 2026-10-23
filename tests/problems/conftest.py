import os

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if os.environ.get("ORIGINAL_VERSION") != "1":
        return
    if report.skipped:
        report.outcome = "failed"
        report.longrepr = "the test is skipped on the original version"
    elif report.when != "call":
        return
    elif report.failed:
        report.outcome = "passed"
        report.longrepr = None
    elif report.passed:
        report.outcome = "failed"
        report.longrepr = "the test passes on the original version"
