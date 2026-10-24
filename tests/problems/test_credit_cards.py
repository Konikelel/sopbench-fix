from tests import harness as H
from tests.agents import executable_paths, ideal_agent, ideal_calls
from tests.labels import label_mismatches


def test_ideal_agent_completes_the_credit_card_tasks_with_a_known_identification():
    tasks = [t for t in H.load_tasks("bank") if t["user_goal"] in ("cancel_credit_card", "pay_bill_with_credit_card")
             and t["action_should_succeed"] and "identification" in t["user_known"]]
    results = ideal_agent("bank", tasks)
    assert len(tasks) == 6 and all(passed > 0 for passed, _ in results.values())


def test_strict_agrees_with_every_bank_label():
    assert label_mismatches("bank", H.load_tasks("bank")) == []


def test_apply_credit_card_adds_a_card_to_the_account():
    tasks = [t for t in H.load_tasks("bank") if t["user_goal"] == "apply_credit_card" and t["action_should_succeed"]]
    for task in tasks:
        username = task["user_known"]["username"]
        entry, _ = H.simulate("bank", task, ideal_calls(task, executable_paths("bank", task)[0]))
        cards = entry["interactions"][0]["database"]["accounts"][username]["credit_cards"]
        assert len(cards) == len(task["initial_database"]["accounts"][username]["credit_cards"]) + 1, task["id"]
    assert len(tasks) == 4
