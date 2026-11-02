import pytest

from tests import harness as H
from tests.agents import ideal_calls, longest_path


@pytest.mark.parametrize("task_id", ["transfer_funds#9", "pay_bill#0"])
def test_amount_in_cents_is_compared_with_the_balance_in_dollars(task_id):
    task = next(t for t in H.load_tasks("bank") if t["id"] == task_id)
    task["initial_database"]["accounts"][task["user_known"]["username"]]["balance"] = 10.0
    task["user_known"].update(amount=500, unit="cents")
    assert H.run("bank", [(task, ideal_calls(task, longest_path("bank", task)))])[0]["success"]
