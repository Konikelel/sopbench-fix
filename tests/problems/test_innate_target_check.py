import pytest

from tests import harness as H
from tests.agents import arguments, executable_paths, ideal_calls


def task(domain, task_id):
    return next(t for t in H.load_tasks(domain) if t["id"] == task_id)


def target_call(should_fail_task):
    return H.Call(should_fail_task["user_goal"], arguments(should_fail_task, should_fail_task["directed_action_graph"]["nodes"][0][1]))


def test_should_fail_task_allowed_by_the_policy_needs_the_check_the_target_action_fails():
    allowed = task("online_market", "add_review#1")
    known = allowed["user_known"]
    login = H.Call("login_user", {"username": known["username"], "password": known["password"]})
    product = H.Call("get_product_details", {"product_id": known["product_id"]})
    runs = H.run("online_market", [(allowed, []), (allowed, [login]), (allowed, [login, product]),
                                   (allowed, [login, target_call(allowed)])])
    assert [r["success"] for r in runs] == [False, False, True, True]


@pytest.mark.parametrize("domain, task_id", [("healthcare", "add_authorized_provider#1"), ("healthcare", "get_claim_details#1"),
                                             ("online_market", "exchange_product#1"), ("online_market", "exchange_product#2")])
def test_rejected_target_action_call_stands_in_for_the_check_the_policy_allows(domain, task_id):
    allowed = task(domain, task_id)
    calls = ideal_calls(allowed, executable_paths(domain, allowed)[0]) + [target_call(allowed)]
    idle, attempted = H.run(domain, [(allowed, []), (allowed, calls)])
    assert attempted["success"] and not idle["success"]


@pytest.mark.parametrize("task_id, missing, other", [("exchange_product#1", "new_product_id", "old_product_id"),
                                                     ("exchange_product#2", "old_product_id", "new_product_id")])
def test_only_the_check_of_the_missing_product_counts(task_id, missing, other):
    allowed = task("online_market", task_id)
    known = allowed["user_known"]
    login = H.Call("login_user", {"username": known["username"], "password": known["password"]})
    runs = H.run("online_market", [(allowed, [login, H.Call("get_product_details", {"product_id": known[product]})])
                                   for product in (other, missing)])
    assert [r["success"] for r in runs] == [False, True]
