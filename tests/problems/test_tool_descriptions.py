import pytest

from env.variables import domain_assistant_keys

FALSE_CLAIMS = [
    ("bank", "get_bank_maximum_loan_amount", "summing the balances of all user accounts"),
    ("bank", "get_loan", "Returns the amount owed"),
    ("bank", "pay_loan", "dependant on the constraints"),
    ("bank", "pay_loan", "or less"),
    ("online_market", "use_coupon", "cart"),
    ("healthcare", "get_claim_details", "Returns true or false"),
    ("bank", "get_account_balance", "None"),
    ("bank", "get_account_owed_balance", "None"),
    ("bank", "get_safety_box", "None"),
    ("dmv", "get_reg_status", "None"),
    ("dmv", "renew_vehicle", "None"),
    ("dmv", "get_dl_status", "None"),
    ("dmv", "renew_dl", "None"),
    ("library", "get_account_balance", "None"),
    ("library", "update_membership", "None"),
]


@pytest.mark.parametrize("domain, tool, claim", FALSE_CLAIMS)
def test_tool_description_does_not_contradict_the_tool(domain, tool, claim):
    descriptions = {a["name"]: a.get("description", "") for a in domain_assistant_keys[domain].actions}
    assert claim not in descriptions[tool]
