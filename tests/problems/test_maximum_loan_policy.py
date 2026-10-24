from tests import harness as H
from tests.agents import executable_paths, ideal_calls

TOOL = "get_bank_maximum_loan_amount"


def test_asking_for_the_maximum_loan_keeps_every_result():
    plans = [(t, ideal_calls(t, paths[0])) for t in H.load_tasks("bank") if (paths := executable_paths("bank", t))]
    plain = [r["success"] for r in H.run("bank", plans)]
    asked = [r["success"] for r in H.run("bank", [(t, calls + [H.Call(TOOL)]) for t, calls in plans])]
    assert len(plans) == 134 and sum(plain) > 0 and asked == plain
