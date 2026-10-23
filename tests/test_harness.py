import os

from tests import harness as H
from tests.agents import executable_paths, graph_paths, ideal_calls

pytest_plugins = "pytester"


def make_task(nodes, connections, should_succeed=True, user_known=None):
    return {"directed_action_graph": {"nodes": nodes, "connections": connections},
            "user_goal": "target", "action_should_succeed": should_succeed,
            "user_known": user_known or {}}


def test_graph_paths_take_each_or_branch_and_keep_and_order():
    # target needs login, then (check_a or check_b) and check_c
    task = make_task(
        nodes=[["target", {}], "and", ["login", {"u": "user"}], "and", "or",
               ["check_a", {}], ["check_b", {}], ["check_c", {}]],
        connections=[[0, 1], [1, 2], [1, 3], [3, 4], [3, 7], [4, 5], [4, 6]])
    assert [[name for name, _ in p] for p in graph_paths(task)] == [
        ["login", "check_a", "check_c", "target"],
        ["login", "check_b", "check_c", "target"],
    ]


def test_graph_paths_keep_a_repeated_step_once():
    # both checks need the same login
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


def test_scripted_calls_reach_the_official_evaluation():
    task = H.load_tasks("university")[0]
    calls = ideal_calls(task, executable_paths("university", task)[0])
    entry, offered = H.simulate("university", task, calls)
    assert offered == H.offered_tools("university", task) + ["exit_conversation"]
    [evaluation] = H.evaluate("university", [entry])
    assert evaluation["user_goal"] == task["user_goal"]
    assert evaluation["num_function_calls"] == len(calls)


def test_text_reply_is_not_a_tool_call():
    task = H.load_tasks("university")[0]
    [evaluation] = H.run("university", [(task, ["I cannot help with that."])])
    assert evaluation["num_function_calls"] == 0


def test_problem_tests_are_inverted_on_the_original_version(pytester, monkeypatch):
    conftest = os.path.join(os.path.dirname(__file__), "problems", "conftest.py")
    with open(conftest, encoding="utf-8") as f:
        pytester.makeconftest(f.read())
    pytester.makepyfile("def test_fixed():\n    assert True\n\ndef test_still_broken():\n    assert False\n")
    pytester.runpytest().assert_outcomes(passed=1, failed=1)
    monkeypatch.setenv("ORIGINAL_VERSION", "1")
    result = pytester.runpytest()
    result.assert_outcomes(passed=1, failed=1)
    result.stdout.fnmatch_lines(["FAILED test_*::test_fixed*"])
