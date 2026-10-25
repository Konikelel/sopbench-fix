from tests import harness as H

TASK = next(t for t in H.load_tasks("bank") if t["user_goal"] == "get_loan")
CALL = H.Call("internal_check_username_exist", {"username": TASK["user_known"]["username"]})


def executed_calls(calls, max_actions, max_turns):
    entry, _ = H.simulate("bank", TASK, calls, ["--max_num_actions", str(max_actions), "--max_num_turns", str(max_turns)])
    return sum("tool_name" in m for m in entry["interactions"][0]["interaction"])


def test_action_limit_above_the_default_is_used():
    assert executed_calls([CALL] * 40, max_actions=30, max_turns=100) == 30


def test_parallel_calls_stop_at_the_action_limit():
    assert executed_calls([[CALL] * 3] * 40, max_actions=10, max_turns=20) == 10


def test_turn_limit_above_the_default_is_used():
    assert executed_calls([CALL] * 40, max_actions=100, max_turns=40) == 20
