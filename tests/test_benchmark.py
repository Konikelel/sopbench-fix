import pytest

from tests import harness as H
from tests.agents import ideal_agent, idle_agent
from tests.labels import label_mismatches

IDLE_PASSES = {
    "bank": {"deposit_funds#1", "deposit_funds#3", "exchange_foreign_currency#3", "transfer_funds#1"},
    "dmv": set(),
    "healthcare": {"reactivate_policy#1", "reactivate_policy#5", "submit_claim#3", "submit_claim#6", "submit_claim#14",
                   "submit_claim#15", "submit_claim#21", "submit_claim#22", "update_policy#3", "update_policy#5",
                   "update_policy#8", "update_policy#14", "update_policy#16", "update_policy#19", "update_policy#20",
                   "update_policy#23", "update_policy#26", "update_policy#30", "update_policy#31", "update_policy#35",
                   "update_policy#37", "update_policy#39", "update_policy#42", "update_policy#44"},
    "library": {"add_book#1"},
    "online_market": {"add_review#5", "add_review#13", "add_review#16", "add_review#19", "add_review#31",
                      "add_review#35", "add_review#39", "add_review#47", "exchange_product#3"},
    "hotel": {"process_guest_checkout#3", "process_guest_checkout#7"},
    "university": set(),
}


@pytest.mark.parametrize("domain", H.domains())
def test_ideal_agent_passes_every_task_on_every_path(domain):
    results = ideal_agent(domain, H.load_tasks(domain))
    assert {t: r for t, r in results.items() if not 0 < r[0] == r[1]} == {}


@pytest.mark.parametrize("domain", H.domains())
def test_labels_agree_with_strict(domain):
    assert label_mismatches(domain, H.load_tasks(domain)) == []


@pytest.mark.parametrize("domain", H.domains())
def test_idle_agent_passes_only_tasks_decided_without_a_tool(domain):
    results = idle_agent(domain, H.load_tasks(domain))
    assert {t for t, success in results.items() if success} == IDLE_PASSES[domain]
