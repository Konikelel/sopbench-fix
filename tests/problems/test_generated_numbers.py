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
