from tests import harness as H
from tests.agents import arguments, executable_paths, ideal_calls


def honest_run(domain, task_id):
    task = next(t for t in H.load_tasks(domain) if t["id"] == task_id)
    target = H.Call(task["user_goal"], arguments(task, task["directed_action_graph"]["nodes"][0][1]))
    return task, ideal_calls(task, executable_paths(domain, task)[0]), target


def test_forbidden_target_sent_as_second_call_is_scored():
    task, calls, target = honest_run("university", "request_graduation#1")
    [evaluation] = H.run("university", [(task, calls[:-1] + [[calls[-1], target]])])
    assert evaluation["action_successfully_called"]
    assert not evaluation["success"]


def test_check_sent_with_the_target_does_not_precede_it():
    task, calls, _ = honest_run("university", "request_graduation#0")
    assert task["action_should_succeed"]
    [evaluation] = H.run("university", [(task, calls[:-2] + [calls[-2:]])])
    assert evaluation["action_successfully_called"]
    assert not evaluation["dirgraph_satisfied"]


def test_honest_checks_sent_together_pass():
    task, calls, _ = honest_run("university", "request_graduation#0")
    [evaluation] = H.run("university", [(task, [calls[:2]] + calls[2:])])
    assert evaluation["success"]


def test_null_call_beside_a_real_one_does_not_shift_pairing():
    task, calls, _ = honest_run("university", "request_graduation#0")
    [evaluation] = H.run("university", [(task, [[H.Call("null"), calls[0]]] + calls[1:])])
    assert evaluation["success"]


def test_na_call_beside_a_real_one_does_not_break_scoring():
    task, calls, _ = honest_run("university", "request_graduation#0")
    [evaluation] = H.run("university", [(task, calls[:-1] + [[H.Call("N/A"), calls[-1]]])])
    assert not evaluation["action_successfully_called"]
