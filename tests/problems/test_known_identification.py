from tests import harness as H
from tests.agents import executable_paths, ideal_agent, ideal_calls

TASK_IDS = ["get_loan#0", "get_loan#5", "pay_bill#0", "pay_loan#0", "pay_loan#1", "set_safety_box#0",
            "set_safety_box#13", "transfer_funds#9"]


def tasks():
    return [t for t in H.load_tasks("bank") if t["id"] in TASK_IDS]


def test_ideal_agent_passes_every_task():
    results = ideal_agent("bank", tasks())
    assert len(results) == 8 and all(passed > 0 for passed, _ in results.values())


def test_made_up_identification_fails_the_task():
    runs = [(t, [H.Call(c.name, {**c.arguments, "identification": "MADE_UP"} if c.name == "login_user" else c.arguments)
                 for c in ideal_calls(t, path)])
            for t in tasks() for path in executable_paths("bank", t)]
    results = H.run("bank", runs)
    assert len(results) == 10 and not any(r["success"] for r in results)
