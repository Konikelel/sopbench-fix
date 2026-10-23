"""Problem tests: each one reproduces a single SOPBench problem and passes once the problem is fixed.

CI also runs them against the original upstream code with ORIGINAL_VERSION=1. There every test
must fail, so the outcome of the test body is inverted: a failing test is reported as passed and
a passing one as failed. Errors in setup, teardown or collection are not inverted.
"""
import os

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if os.environ.get("ORIGINAL_VERSION") != "1" or report.when != "call":
        return
    if report.failed:
        report.outcome = "passed"
        report.longrepr = None
    elif report.passed:
        report.outcome = "failed"
        report.longrepr = "the test passes on the original version"
