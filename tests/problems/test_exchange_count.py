from tests import harness as H
from tests.agents import executable_paths, ideal_calls


def task_and_calls():
    task = next(t for t in H.load_tasks("online_market") if t["id"] == "exchange_product#12")
    return task, ideal_calls(task, executable_paths("online_market", task)[0])


def test_an_exchange_past_the_maximum_number_of_exchanges_violates_the_constraint():
    task, calls = task_and_calls()
    exchange = calls[-1].arguments
    swap_back = {**exchange, "old_product_id": exchange["new_product_id"], "new_product_id": exchange["old_product_id"]}
    up_to_maximum = calls + [H.Call("exchange_product", swap_back)]
    past_maximum = up_to_maximum + [H.Call("exchange_product", exchange)]
    results = H.run("online_market", [(task, up_to_maximum), (task, past_maximum)])
    assert [r["constraint_not_violated"] for r in results] == [True, False]


def test_exchanging_an_order_placed_in_the_same_episode_replays_without_error():
    task, calls = task_and_calls()
    exchange = calls[-1].arguments
    calls[-1:] = [H.Call("add_to_cart", {"username": exchange["username"], "product_id": exchange["old_product_id"], "quantity": 1}),
                  H.Call("place_order", {"username": exchange["username"]}),
                  H.Call("exchange_product", {**exchange, "order_id": "ORD-4"})]
    assert H.run("online_market", [(task, calls)])[0]["no_tool_call_error"]
