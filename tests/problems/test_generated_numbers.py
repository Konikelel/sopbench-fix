import json
import os
import subprocess
import sys

import pytest

from tests import harness as H
from tests.agents import executable_paths, ideal_calls

EVALUATE_SCRIPT = ("import json, sys; from tests import harness as H; "
                   "print(json.dumps(H.evaluate(sys.argv[1], json.load(sys.stdin))))")


def evaluate_with_another_hash_seed(domain, entries):
    seed = "2" if os.environ.get("PYTHONHASHSEED") == "1" else "1"
    result = subprocess.run([sys.executable, "-c", EVALUATE_SCRIPT, domain], input=json.dumps(entries), capture_output=True,
                            text=True, cwd=H.ROOT, env={**os.environ, "PYTHONHASHSEED": seed})
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("domain, goal", [("dmv", "update_test_status"), ("bank", "apply_credit_card")])
def test_ideal_agent_passes_when_simulation_and_evaluation_run_in_separate_processes(domain, goal):
    tasks = [t for t in H.load_tasks(domain) if t["user_goal"] == goal and t["action_should_succeed"]]
    entries = [H.simulate(domain, t, ideal_calls(t, executable_paths(domain, t)[0]))[0] for t in tasks]
    assert tasks and all(e["interactions"][0]["database"] != e["task"]["initial_database"] for e in entries)
    assert all(e["success"] for e in evaluate_with_another_hash_seed(domain, entries))


CARD_TASK_IDS = ["apply_credit_card#0", "apply_credit_card#2", "apply_credit_card#4", "apply_credit_card#6"]


def swap_int_and_float(value):
    if type(value) is int:
        return float(value)
    return int(value) if isinstance(value, float) and value.is_integer() else value


@pytest.mark.parametrize("task_id", CARD_TASK_IDS)
def test_card_number_does_not_depend_on_how_the_numbers_are_written(task_id):
    task = next(t for t in H.load_tasks("bank") if t["id"] == task_id)
    calls = ideal_calls(task, executable_paths("bank", task)[0])
    rewritten = [H.Call(c.name, {k: swap_int_and_float(v) for k, v in c.arguments.items()}) for c in calls]
    assert task["action_should_succeed"] and json.dumps([c.arguments for c in rewritten]) != json.dumps([c.arguments for c in calls])
    entry, rewritten_entry = (H.simulate("bank", task, plan)[0] for plan in (calls, rewritten))
    database = entry["interactions"][0]["database"]
    assert database != task["initial_database"]
    assert rewritten_entry["interactions"][0]["database"] == database
