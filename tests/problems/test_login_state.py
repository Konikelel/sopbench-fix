import pytest

from tests import harness as H
from tests.agents import executable_paths, ideal_calls
from tests.labels import strict_system

CREDENTIAL_CHECKS = {"login_user": "logged_in_user", "authenticate_admin_password": "authenticated_admin_password"}


def task(domain, task_id):
    return next(t for t in H.load_tasks(domain) if t["id"] == task_id)


@pytest.mark.parametrize("domain, task_id", [("bank", "apply_credit_card#4"), ("bank", "close_account#0"),
                                             ("dmv", "cancel_test#0"), ("healthcare", "add_authorized_provider#0"),
                                             ("library", "add_book#0"), ("online_market", "add_review#0"),
                                             ("university", "apply_financial_aid#0")])
def test_wrong_credential_fails_the_task(domain, task_id):
    should_succeed_task = task(domain, task_id)
    honest = ideal_calls(should_succeed_task, executable_paths(domain, should_succeed_task)[0])
    wrong = [H.Call(c.name, {k: v if k == "username" or c.name not in CREDENTIAL_CHECKS else "WRONG_CREDENTIAL"
                             for k, v in c.arguments.items()}) for c in honest]
    honest_run, wrong_run = H.run(domain, [(should_succeed_task, honest), (should_succeed_task, wrong)])
    assert honest_run["success"] and not wrong_run["success"]


@pytest.mark.parametrize("domain, task_id, action", [("bank", "close_account#0", "login_user"),
                                                     ("bank", "close_account#0", "authenticate_admin_password"),
                                                     ("dmv", "cancel_test#0", "login_user"),
                                                     ("dmv", "cancel_test#0", "authenticate_admin_password"),
                                                     ("healthcare", "add_authorized_provider#0", "login_user"),
                                                     ("library", "add_book#0", "login_user"),
                                                     ("online_market", "add_review#0", "login_user"),
                                                     ("university", "apply_financial_aid#0", "login_user")])
def test_wrong_credential_leaves_the_strict_state_unchanged(domain, task_id, action):
    t = task(domain, task_id)
    strict = strict_system(domain, t)
    username = t["user_known"]["username"]
    if action != "login_user":
        login = next(c for c in ideal_calls(t, executable_paths(domain, t)[0]) if c.name == "login_user")
        assert strict.login_user(**login.arguments)
    assert getattr(strict, action)(username, "WRONG_CREDENTIAL") is False
    assert not getattr(strict.evaluation_get_state_tracker(), CREDENTIAL_CHECKS[action])(username)
