from tests import harness as H
from tests.agents import executable_paths, ideal_calls

TASK_IDS = ["cancel_credit_card#3", "pay_bill_with_credit_card#0"]


def test_ideal_agent_passes_the_login_path_only_with_the_known_identification():
    runs = [(t, ideal_calls(t, p)) for t in H.load_tasks("bank") if t["id"] in TASK_IDS
            for p in executable_paths("bank", t) if "get_credit_card_info" in [name for name, _ in p]]
    made_up = [(t, [H.Call(c.name, {**c.arguments, "identification": "MADE_UP"} if c.name == "login_user" else c.arguments)
                    for c in calls]) for t, calls in runs]
    results = [(t["id"], r["success"]) for (t, _), r in zip(runs + made_up, H.run("bank", runs + made_up))]
    assert results == [(i, True) for i in TASK_IDS] + [(i, False) for i in TASK_IDS]
