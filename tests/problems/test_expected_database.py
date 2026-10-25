import pytest

from tests import harness as H
from tests.agents import executable_paths, ideal_calls


def ideal(domain, task):
    paths = executable_paths(domain, task)
    return ideal_calls(task, paths[0]) if paths else []


def close_account_calls(task):
    known = task["user_known"]
    return [H.Call("login_user", {"username": known["username"], "identification": known["identification"]}),
            H.Call("authenticate_admin_password", {"username": known["username"], "admin_password": known["admin_password"]}),
            H.Call("close_account", {"username": known["username"]})]


@pytest.mark.parametrize("should_succeed", [True, False])
def test_unrequested_account_closure_fails(should_succeed):
    tasks = [t for t in H.load_tasks("bank") if t["action_should_succeed"] == should_succeed
             and t["user_goal"] != "close_account" and {"identification", "admin_password"} <= set(t["user_known"])]
    honest = H.run("bank", [(t, ideal("bank", t)) for t in tasks])
    honest_tasks = [t for t, e in zip(tasks, honest) if e["success"]]
    entries = [H.simulate("bank", t, ideal("bank", t) + close_account_calls(t))[0] for t in honest_tasks]
    closed = [e["task"]["user_known"]["username"] not in e["interactions"][0]["database"]["accounts"] for e in entries]
    assert honest_tasks and all(closed)
    assert not any(e["success"] for e in H.evaluate("bank", entries))


@pytest.mark.parametrize("change", ["doubled", "repeated", "doubled_then_right"])
def test_wrong_database_write_fails(change):
    task = next(t for t in H.load_tasks("bank") if t["id"] == "transfer_funds#20")
    calls = ideal("bank", task)
    *checks, target = calls
    doubled = H.Call(target.name, {**target.arguments, "amount": 2 * target.arguments["amount"]})
    wrong = {"doubled": checks + [doubled], "repeated": calls + [target], "doubled_then_right": checks + [doubled, target]}
    honest_run, wrong_run = H.run("bank", [(task, calls), (task, wrong[change])])
    assert honest_run["success"] and not wrong_run["success"]
