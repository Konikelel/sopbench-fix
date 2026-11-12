from env.task import get_dep_verb, get_default_dep_full
from env.variables import domain_keys
from tests import harness as H


def render(domain, tree, params):
    return get_dep_verb(domain, tree, params, "structured")


def changed(value):
    if isinstance(value, list):
        return value + ["~"]
    if isinstance(value, str):
        return value + "~"
    return value + 12345


def shown_thresholds(domain, task):
    prompt = H.assistant_info(domain, task)["instructions"]
    trees = {**get_default_dep_full(domain, "full", False), task["user_goal"]: task["constraints_original"]}
    candidates = [task["constraint_parameters"], domain_keys[domain + "_strict"]().evaluation_get_dependency_parameters()]
    shown = {}
    for action, tree in trees.items():
        if not tree:
            continue
        params = next(p for p in candidates if f"* {action}:\n{render(domain, tree, p)}\n\n" in prompt)
        for key, value in params.items():
            if render(domain, tree, params) != render(domain, tree, {**params, key: changed(value)}):
                shown.setdefault(key, set()).add(repr(value))
    return shown


def test_other_actions_show_the_thresholds_of_the_task():
    task = next(t for t in H.load_tasks("bank") if t["id"] == "get_loan#7")
    prompt = H.assistant_info("bank", task)["instructions"]
    for action in ["get_loan", "apply_credit_card", "set_safety_box"]:
        section = prompt.split(f"* {action}:\n")[1].split("\n\n")[0]
        assert "credit score higher than the 350 credit score" in section


def test_no_prompt_shows_two_values_of_one_threshold():
    two_values = [(domain, task["id"]) for domain in H.domains() for task in H.load_tasks(domain)
                  if any(len(values) > 1 for values in shown_thresholds(domain, task).values())]
    assert two_values == []
