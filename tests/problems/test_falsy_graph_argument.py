import pytest

from tests import harness as H
from tests.agents import executable_paths, ideal_calls


@pytest.mark.parametrize("slots", [[], ""])
def test_falsy_argument_must_match_the_checked_one(slots):
    task = next(t for t in H.load_tasks("library") if t["id"] == "reserve_room#0")
    calls = ideal_calls(task, executable_paths("library", task)[0])
    *checks, target = calls
    changed = checks + [H.Call(target.name, {**target.arguments, "slots": slots})]
    honest_run, changed_run = H.run("library", [(task, calls), (task, changed)])
    assert honest_run["dirgraph_satisfied"] and not changed_run["dirgraph_satisfied"]
