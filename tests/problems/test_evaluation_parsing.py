import pytest

from tests import harness as H
from tests.agents import arguments, executable_paths, ideal_calls


def task(domain, task_id):
    return next(t for t in H.load_tasks(domain) if t["id"] == task_id)


def ideal_run(domain, task_id):
    ideal_task = task(domain, task_id)
    [evaluation] = H.run(domain, [(ideal_task, ideal_calls(ideal_task, executable_paths(domain, ideal_task)[0]))])
    return evaluation


def test_evaluation_does_not_execute_tool_responses(tmp_path):
    marker = tmp_path / "marker"
    payload = f"__import__('pathlib').Path(r'{marker}').touch()"
    H.run("bank", [(task("bank", "set_safety_box#0"),
                    [H.Call("set_safety_box", {"username": "john_doe", "safety_box_new": payload}),
                     H.Call("get_safety_box", {"username": "john_doe"})])])
    assert not marker.exists()


@pytest.mark.parametrize("domain, task_id", [("dmv", "update_test_status#0"), ("library", "add_book#0"),
                                             ("hotel", "process_guest_checkout#0")])
def test_boolean_arguments_are_read_as_json(domain, task_id):
    assert ideal_run(domain, task_id)["success"]


def test_date_responses_are_compared_as_text():
    assert ideal_run("dmv", "renew_vehicle#2")["constraint_not_violated"]


@pytest.mark.parametrize("domain, task_id", [("bank", "get_account_owed_balance#0"), ("dmv", "renew_vehicle#0"),
                                             ("healthcare", "get_policy_details#0"), ("library", "check_return_date#0"),
                                             ("online_market", "get_order_details#0"),
                                             ("hotel", "process_guest_checkin#0")])
def test_target_action_returning_a_value_counts_as_called(domain, task_id):
    assert ideal_run(domain, task_id)["success"]


@pytest.mark.parametrize("domain, task_id", [("bank", "get_account_owed_balance#1"), ("bank", "transfer_funds#1"),
                                             ("dmv", "renew_dl#3"), ("dmv", "renew_vehicle#5"), ("dmv", "renew_vehicle#8"),
                                             ("healthcare", "add_authorized_provider#1"), ("healthcare", "get_claim_details#2"),
                                             ("healthcare", "get_policy_details#2"), ("healthcare", "reactivate_policy#1"),
                                             ("library", "check_return_date#1"), ("library", "show_available_rooms#2"),
                                             ("online_market", "add_review#1"), ("online_market", "exchange_product#1"),
                                             ("online_market", "exchange_product#2"), ("online_market", "exchange_product#3"),
                                             ("online_market", "get_order_details#1")])
def test_calling_a_forbidden_target_action_fails_the_task(domain, task_id):
    should_fail_task = task(domain, task_id)
    honest = ideal_calls(should_fail_task, executable_paths(domain, should_fail_task)[0])
    target = H.Call(should_fail_task["user_goal"], arguments(should_fail_task, should_fail_task["directed_action_graph"]["nodes"][0][1]))
    honest_run, forbidden_run = H.run(domain, [(should_fail_task, honest), (should_fail_task, honest + [target])])
    assert honest_run["success"] and not forbidden_run["success"]
