from tests import harness as H
from tests.agents import graph_paths, ideal_calls


def plans(domain, task_id):
    task = next(t for t in H.load_tasks(domain) if t["id"] == task_id)
    return task, {tuple(c.name for c in calls): calls for calls in (ideal_calls(task, p) for p in graph_paths(task))}


def test_should_succeed_task_needs_the_check_of_a_satisfied_alternative():
    task, by_names = plans("library", "borrow_book#7")
    violated = by_names[("login_user", "internal_check_book_available", "internal_is_restricted", "borrow_book")]
    satisfied = by_names[("login_user", "internal_check_book_available", "internal_get_membership_status",
                          "internal_get_interaction_date", "borrow_book")]
    runs = H.run("library", [(task, violated), (task, satisfied)])
    assert [r["success"] for r in runs] == [False, True]


def test_should_fail_task_needs_the_checks_of_all_violated_alternatives():
    task, by_names = plans("healthcare", "schedule_appointment#6")
    one = by_names[("login_user", "get_policy_details")]
    both = by_names[("get_provider_details", "login_user", "get_policy_details")]
    runs = H.run("healthcare", [(task, one), (task, both)])
    assert [r["success"] for r in runs] == [False, True]
