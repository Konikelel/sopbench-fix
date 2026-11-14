import pytest

from tests import harness as H
from tests.agents import executable_paths, ideal_calls, responses


@pytest.mark.parametrize("domain, task_id, parameter", [
    ("healthcare", "reactivate_policy#0", "annual_income"),
    ("online_market", "add_review#0", "rating"),
    ("hotel", "place_room_service_order#1", "amount"),
])
def test_a_number_given_as_a_string_is_rejected_by_the_tool_and_by_the_evaluation(domain, task_id, parameter):
    task = next(t for t in H.load_tasks(domain) if t["id"] == task_id)
    calls = ideal_calls(task, executable_paths(domain, task)[0])
    target = calls[-1]
    assert target.name == task["user_goal"] and isinstance(target.arguments[parameter], (int, float))
    as_string = calls[:-1] + [H.Call(target.name, {**target.arguments, parameter: str(target.arguments[parameter])})]
    entries = [H.simulate(domain, task, plan)[0] for plan in (calls, as_string)]
    assert responses(entries[0])[-1] == "True"
    assert responses(entries[1])[-1].startswith("TypeError")
    assert [e["success"] for e in H.evaluate(domain, entries)] == [True, False]
