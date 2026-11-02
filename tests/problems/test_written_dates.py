from tests import harness as H
from tests.agents import executable_paths, ideal_calls


def task_and_calls(domain, task_id):
    task = next(t for t in H.load_tasks(domain) if t["id"] == task_id)
    return task, ideal_calls(task, executable_paths(domain, task)[0])


def replays_without_error(domain, task, calls):
    return H.run(domain, [(task, calls)])[0]["no_tool_call_error"]


def test_appealing_a_claim_submitted_in_the_same_episode_replays_without_error():
    task, calls = task_and_calls("healthcare", "submit_claim#0")
    username = task["user_known"]["username"]
    calls.append(H.Call("appeal_claim", {"username": username, "claim_id": "CLM-2"}))
    assert replays_without_error("healthcare", task, calls)


def test_updating_a_policy_reactivated_in_the_same_episode_replays_without_error():
    task, calls = task_and_calls("healthcare", "reactivate_policy#0")
    calls.append(H.Call("update_policy", calls[-1].arguments))
    assert replays_without_error("healthcare", task, calls)


def test_returning_an_order_placed_in_the_same_episode_replays_without_error():
    task, calls = task_and_calls("online_market", "return_order#2")
    username = task["user_known"]["username"]
    calls[-1:] = [H.Call("add_to_cart", {"username": username, "product_id": "Headphones", "quantity": 1}),
                  H.Call("place_order", {"username": username}),
                  H.Call("return_order", {"username": username, "order_id": "ORD-4"})]
    assert replays_without_error("online_market", task, calls)
