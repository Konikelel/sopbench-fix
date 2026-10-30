import pytest

from tests import harness as H
from tests.agents import arguments, executable_paths, ideal_calls

TASKS = [("dmv", "renew_dl#3"), ("online_market", "get_order_details#1")]


def should_fail_run(domain, task_id):
    task = next(t for t in H.load_tasks(domain) if t["id"] == task_id)
    assert not task["action_should_succeed"]
    target = H.Call(task["user_goal"], arguments(task, task["directed_action_graph"]["nodes"][0][1]))
    return task, ideal_calls(task, executable_paths(domain, task)[0]), target


@pytest.mark.parametrize("domain, task_id", TASKS)
@pytest.mark.parametrize("ending_call", ["exit_conversation", "none", "N/A"])
def test_forbidden_target_sent_with_a_message_ending_call_fails_the_task(domain, task_id, ending_call):
    task, honest, target = should_fail_run(domain, task_id)
    honest_run, forbidden_run = H.run(domain, [(task, honest), (task, honest + [[target, H.Call(ending_call)]])])
    assert honest_run["success"] and not forbidden_run["success"]


@pytest.mark.parametrize("domain, task_id", TASKS)
def test_forbidden_target_cut_off_by_the_action_limit_fails_the_task(domain, task_id):
    task, honest, target = should_fail_run(domain, task_id)
    flags = ["--max_num_actions", str(len(honest) + 1)]
    entry, _ = H.simulate(domain, task, honest + [[honest[-1], target]], flags)
    [evaluation] = H.evaluate(domain, [entry])
    assert not any(m.get("tool_name") == task["user_goal"] for m in entry["interactions"][0]["interaction"])
    assert not evaluation["success"]
