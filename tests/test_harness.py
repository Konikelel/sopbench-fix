import itertools
import os

import pytest

from tests import harness as H
from tests.agents import branch_orders, executable_paths, graph_paths, ideal_calls, ideal_plan, reactive_paths

pytest_plugins = "pytester"


def make_task(nodes, connections, should_succeed=True, user_known=None):
    return {"directed_action_graph": {"nodes": nodes, "connections": connections},
            "user_goal": "target", "action_should_succeed": should_succeed,
            "user_known": user_known or {}}


def test_graph_paths_take_each_or_branch_and_keep_and_order():
    task = make_task(
        nodes=[["target", {}], "and", ["login", {"u": "user"}], "and", "or",
               ["check_a", {}], ["check_b", {}], ["check_c", {}]],
        connections=[[0, 1], [1, 2], [1, 3], [3, 4], [3, 7], [4, 5], [4, 6]])
    assert [[name for name, _ in p] for p in graph_paths(task)] == [
        ["login", "check_a", "check_c", "target"],
        ["login", "check_b", "check_c", "target"],
    ]


def test_graph_paths_keep_a_repeated_step_once():
    task = make_task(
        nodes=[["target", {}], "and", ["check_a", {}], ["check_b", {}], ["login", {"u": "user"}]],
        connections=[[0, 1], [1, 2], [1, 3], [2, 4], [3, 4]])
    assert [[name for name, _ in p] for p in graph_paths(task)] == [["login", "check_a", "check_b", "target"]]


def test_graph_paths_list_identical_paths_once():
    task = make_task(nodes=[["target", {}], "or", ["check", {}], ["check", {}]],
                     connections=[[0, 1], [1, 2], [1, 3]])
    assert graph_paths(task) == [[("check", {}), ("target", {})]]


def test_ideal_calls_take_arguments_from_user_known_and_skip_target_when_it_should_fail():
    nodes = [["target", {"amount": "amount"}], ["login", {"username": "user", "password": "pw"}]]
    known = {"user": "alice", "amount": 5}
    path = graph_paths(make_task(nodes, [[0, 1]]))[0]
    assert ideal_calls(make_task(nodes, [[0, 1]], True, known), path) == [
        H.Call("login", {"username": "alice"}), H.Call("target", {"amount": 5})]
    assert ideal_calls(make_task(nodes, [[0, 1]], False, known), path) == [H.Call("login", {"username": "alice"})]


def test_executable_paths_use_only_offered_tools():
    task = next(t for t in H.load_tasks("bank")
                if any(n[0] == "internal_get_database" for n in t["directed_action_graph"]["nodes"]
                       if not isinstance(n, str)))
    offered = set(H.offered_tools("bank", task))
    paths = executable_paths("bank", task)
    assert len(paths) < len(graph_paths(task))
    assert all(c.name in offered for p in paths for c in ideal_calls(task, p))


def test_executable_paths_of_a_should_succeed_task_go_only_through_the_satisfied_alternative():
    task = next(t for t in H.load_tasks("bank") if t["id"] == "pay_loan#1")
    [path] = executable_paths("bank", task)
    assert [name for name, _ in path] == ["login_user", "internal_check_username_exist", "get_account_balance",
                                          "get_account_owed_balance", "pay_loan"]
    _, entry, _ = ideal_plan("bank", task, path)
    assert H.evaluate("bank", [entry])[0]["success"]


@pytest.mark.parametrize("domain, task_id, unreachable", [("healthcare", "submit_claim#0", "get_claim_details"),
                                                          ("healthcare", "submit_claim#1", "get_claim_details"),
                                                          ("bank", "cancel_credit_card#3", "authenticate_admin_password")])
def test_executable_paths_skip_a_call_with_an_argument_nothing_earlier_gives(domain, task_id, unreachable):
    task = next(t for t in H.load_tasks(domain) if t["id"] == task_id)
    assert any(name == unreachable for p in graph_paths(task) for name, _ in p)
    paths = executable_paths(domain, task)
    assert paths and not any(name == unreachable for p in paths for name, _ in p)


def test_ideal_agent_stops_a_should_fail_path_at_a_gate_it_has_no_credential_for():
    task = next(t for t in H.load_tasks("bank") if t["id"] == "get_loan#1")
    [path] = executable_paths("bank", task)
    calls, entry, _ = ideal_plan("bank", task, path)
    assert calls == [H.Call("login_user", {"username": task["user_known"]["username"]})]
    assert H.evaluate("bank", [entry])[0]["success"]


def test_executable_paths_of_a_should_fail_task_skip_a_gate_without_a_credential_after_a_successful_login():
    task = next(t for t in H.load_tasks("bank") if t["id"] == "cancel_credit_card#9")
    [path] = executable_paths("bank", task)
    assert [name for name, _ in path] == ["internal_check_username_exist", "login_user", "get_credit_card_info",
                                          "cancel_credit_card"]


def test_ideal_agent_stops_a_should_fail_path_at_a_failed_login():
    task = next(t for t in H.load_tasks("bank") if t["id"] == "get_loan#3")
    [path] = executable_paths("bank", task)
    calls, entry, _ = ideal_plan("bank", task, path)
    assert [c.name for c in calls] == ["login_user"]
    assert H.evaluate("bank", [entry])[0]["success"]


def test_ideal_agent_calls_a_should_fail_target_that_the_policy_allows():
    task = next(t for t in H.load_tasks("online_market") if t["id"] == "add_review#1")
    [path] = executable_paths("online_market", task)
    calls, entry, _ = ideal_plan("online_market", task, path)
    assert [c.name for c in calls] == ["login_user", "add_review"]
    assert H.evaluate("online_market", [entry])[0]["success"]


def test_ideal_agent_takes_an_argument_missing_from_user_known_from_an_earlier_response():
    task = next(t for t in H.load_tasks("university") if t["id"] == "declare_minor#0")
    [path] = executable_paths("university", task)
    calls, entry, _ = ideal_plan("university", task, path)
    assert H.Call("internal_get_major_info", {"major": "Computer Science"}) in calls
    assert H.evaluate("university", [entry])[0]["success"]


def test_scripted_calls_reach_the_official_evaluation():
    task = H.load_tasks("university")[0]
    calls = ideal_calls(task, executable_paths("university", task)[0])
    entry, offered = H.simulate("university", task, calls)
    assert offered == H.offered_tools("university", task) + ["exit_conversation"]
    [evaluation] = H.evaluate("university", [entry])
    assert evaluation["user_goal"] == task["user_goal"]
    assert evaluation["num_function_calls"] == len(calls)


@pytest.mark.parametrize("arguments", ["{not json", None, "[" * 1100, "9" * 5000])
def test_unparsable_arguments_of_an_unknown_tool_are_a_tool_call_error(arguments):
    task = H.load_tasks("university")[0]
    entry, _ = H.simulate("university", task, [H.Call("no_such_tool")])
    [call] = [c for m in entry["interactions"][0]["interaction"] for c in m.get("tool_calls") or []
              if c["function"]["name"] == "no_such_tool"]
    call["function"]["arguments"] = arguments
    [evaluation] = H.evaluate("university", [entry])
    assert not evaluation["no_tool_call_error"]


def test_problem_tests_are_inverted_on_the_original_version(pytester, monkeypatch):
    conftest = os.path.join(os.path.dirname(__file__), "problems", "conftest.py")
    with open(conftest, encoding="utf-8") as f:
        pytester.makeconftest(f.read())
    pytester.makepyfile("import pytest\n\n"
                        "def test_fixed():\n    assert True\n\n"
                        "def test_still_broken():\n    assert False\n\n"
                        "@pytest.mark.skip\ndef test_skipped():\n    pass\n")
    pytester.runpytest().assert_outcomes(passed=1, failed=1, skipped=1)
    monkeypatch.setenv("ORIGINAL_VERSION", "1")
    result = pytester.runpytest()
    result.assert_outcomes(passed=1, failed=1, errors=1)
    result.stdout.fnmatch_lines(["FAILED test_*::test_fixed*", "ERROR test_*::test_skipped*"])


def test_should_fail_path_ends_at_the_check_that_violates_the_policy():
    task = next(t for t in H.load_tasks("bank") if t["id"] == "set_safety_box#29")
    [path] = executable_paths("bank", task)
    calls, entry, _ = ideal_plan("bank", task, path)
    assert [c.name for c in calls] == ["login_user", "authenticate_admin_password", "internal_check_username_exist",
                                       "get_account_balance"]
    assert [name for name, _ in graph_paths(task)[0]][-2:] == ["internal_get_credit_score", "set_safety_box"]
    assert H.evaluate("bank", [entry])[0]["success"]


def test_reactive_paths_check_unsatisfied_alternatives_in_every_order_before_the_satisfied_one():
    raw = graph_paths(make_task(
        nodes=[["target", {}], "and", ["login", {}], "or", ["check_a", {}], ["check_b", {}], ["check_c", {}]],
        connections=[[0, 1], [1, 2], [1, 3], [3, 4], [3, 5], [3, 6]]))
    complete = graph_paths(make_task(nodes=[["target", {}], "and", ["login", {}], ["check_c", {}]],
                                     connections=[[0, 1], [1, 2], [1, 3]]))
    assert [[name for name, _ in p] for p in complete + reactive_paths(raw, complete)] == [
        ["login", "check_c", "target"],
        ["login", "check_a", "check_c", "target"],
        ["login", "check_a", "check_b", "check_c", "target"],
        ["login", "check_b", "check_c", "target"],
        ["login", "check_b", "check_a", "check_c", "target"],
    ]


def test_reactive_paths_keep_the_unsatisfied_alternative_of_each_or_at_its_own_node():
    raw = graph_paths(make_task(
        nodes=[["target", {}], "and", "or", ["bad_a", {}], ["good_a", {}], "or", ["bad_b", {}], ["good_b", {}]],
        connections=[[0, 1], [1, 2], [2, 3], [2, 4], [1, 5], [5, 6], [5, 7]]))
    complete = graph_paths(make_task(nodes=[["target", {}], "and", ["good_a", {}], ["good_b", {}]],
                                     connections=[[0, 1], [1, 2], [1, 3]]))
    assert [[name for name, _ in p] for p in reactive_paths(raw, complete)] == [
        ["good_a", "bad_b", "good_b", "target"],
        ["bad_a", "good_a", "good_b", "target"],
        ["bad_a", "good_a", "bad_b", "good_b", "target"],
    ]


def test_reactive_paths_keep_the_and_order_when_a_satisfied_alternative_has_no_tool():
    raw = graph_paths(make_task(
        nodes=[["target", {}], "and", "or", ["bad_a", {}], ["bad_b", {}], "and", "or", ["bad_c", {}], "and"],
        connections=[[0, 1], [1, 2], [2, 3], [2, 4], [2, 5], [1, 6], [6, 7], [6, 8]]))
    complete = graph_paths(make_task(nodes=[["target", {}]], connections=[]))
    assert [[name for name, _ in p] for p in reactive_paths(raw, complete)] == [
        ["bad_c", "target"],
        ["bad_a", "target"],
        ["bad_a", "bad_c", "target"],
        ["bad_a", "bad_b", "target"],
        ["bad_a", "bad_b", "bad_c", "target"],
        ["bad_b", "target"],
        ["bad_b", "bad_c", "target"],
        ["bad_b", "bad_a", "target"],
        ["bad_b", "bad_a", "bad_c", "target"],
    ]


def test_branch_orders_permute_the_alternatives_of_a_violated_or_only():
    dep = ["or", [["single", "a"], ["single", "b"], ["single", "c"]]]
    orders = [[part[1] for part in d[1]] for d in branch_orders(dep, lambda _: True)]
    assert orders == [list(order) for order in itertools.permutations("abc")]
    assert branch_orders(dep, lambda _: False) == [dep]


@pytest.mark.parametrize("task_id", ["borrow_book#7", "borrow_book#12"])
def test_should_succeed_paths_check_the_unsatisfied_alternative_before_the_satisfied_one(task_id):
    task = next(t for t in H.load_tasks("library") if t["id"] == task_id)
    paths = executable_paths("library", task)
    [path] = [p for p in paths if any(name == "internal_is_restricted" for name, _ in p)]
    names = [name for name, _ in path]
    assert len(paths) == 2 and names.index("internal_is_restricted") < names.index("internal_get_membership_status")
    _, entry, _ = ideal_plan("library", task, path)
    assert H.evaluate("library", [entry])[0]["success"]


def test_should_fail_paths_check_the_unsatisfied_alternative_before_the_violated_check():
    task = next(t for t in H.load_tasks("online_market") if t["id"] == "return_order#7")
    plans = [ideal_plan("online_market", task, p) for p in executable_paths("online_market", task)
             if p[0][0] == "internal_get_interaction_time"]
    assert plans and all(calls[-1].name in ("get_order_details", "view_order_history") for calls, _, _ in plans)
    assert all(e["success"] for e in H.evaluate("online_market", [entry for _, entry, _ in plans]))


def test_should_fail_paths_check_the_violated_alternatives_in_either_order():
    task = next(t for t in H.load_tasks("library") if t["id"] == "borrow_book#9")
    plans = [ideal_plan("library", task, p) for p in executable_paths("library", task)]
    names = [[c.name for c in calls] for calls, _, _ in plans]
    assert {n.index("internal_is_restricted") < n.index("internal_get_membership_status") for n in names} == {True, False}
    assert all(e["success"] for e in H.evaluate("library", [entry for _, entry, _ in plans]))


def test_a_merged_path_cut_before_the_unsatisfied_alternative_is_not_a_path():
    task = next(t for t in H.load_tasks("library") if t["id"] == "borrow_book#23")
    [path] = executable_paths("library", task)
    assert ideal_calls(task, path)[-1].name == "internal_get_user_num_borrowed"
