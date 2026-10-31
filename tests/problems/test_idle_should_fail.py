from tests import harness as H
from tests.agents import executable_paths, ideal_calls


def should_fail_plan(domain, task_id):
    task = next(t for t in H.load_tasks(domain) if t["id"] == task_id)
    assert not task["action_should_succeed"]
    return task, ideal_calls(task, executable_paths(domain, task)[0])


def test_should_fail_task_needs_the_check_of_a_violated_constraint():
    task, calls = should_fail_plan("library", "add_book#3")
    login = [c for c in calls if c.name == "login_user"]
    idle, logged_in, checked = H.run("library", [(task, []), (task, login), (task, calls)])
    assert checked["success"] and not logged_in["success"] and not idle["success"]


def test_checks_of_one_violated_constraint_are_enough():
    task, calls = should_fail_plan("dmv", "schedule_test#17")
    setup, attempts, age = calls[:2], calls[2:3], calls[3:]
    assert [c.name for c in attempts + age] == ["internal_get_test_details", "internal_get_interaction_time", "internal_get_user_birthday"]
    runs = H.run("dmv", [(task, setup), (task, setup + attempts), (task, setup + age)])
    assert [r["success"] for r in runs] == [False, True, True]


def test_idle_agent_passes_only_when_the_violated_constraint_needs_no_tool():
    no_tool, _ = should_fail_plan("online_market", "add_review#13")
    needs_tool, _ = should_fail_plan("online_market", "add_review#3")
    no_tool_run, needs_tool_run = H.run("online_market", [(no_tool, []), (needs_tool, [])])
    assert no_tool_run["success"] and not needs_tool_run["success"]


def test_failed_login_stands_in_only_for_checks_that_need_it():
    blocked, plan = should_fail_plan("bank", "pay_bill#1")
    open_check, _ = should_fail_plan("bank", "get_loan#7")
    username = open_check["user_known"]["username"]
    guessed = H.Call("login_user", {"username": username, "identification": "guessed"})
    credit_score = H.Call("internal_get_credit_score", {"username": username})
    identification = blocked["initial_database"]["accounts"][username]["identification"]
    logged_in = H.Call("login_user", {"username": username, "identification": identification})
    runs = H.run("bank", [(blocked, plan[:1]), (blocked, [logged_in]), (open_check, [guessed]),
                          (open_check, [guessed, credit_score])])
    assert [r["success"] for r in runs] == [True, False, False, True]
