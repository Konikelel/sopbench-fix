from tests import harness as H
from tests.agents import executable_paths, ideal_calls


def test_paying_the_late_fee_twice_charges_it_once():
    task = next(t for t in H.load_tasks("library") if t["user_goal"] == "pay_late_fee" and t["action_should_succeed"])
    username = task["user_known"]["username"]
    calls = ideal_calls(task, executable_paths("library", task)[0])
    entry, _ = H.simulate("library", task, calls + [H.Call("pay_late_fee", {"username": username})])
    account = entry["interactions"][0]["database"]["accounts"][username]
    assert (account["balance"], account["late_book_count"]) == (24, 0)
