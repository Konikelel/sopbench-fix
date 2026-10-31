from tests import harness as H
from tests.agents import executable_paths, ideal_calls

TOOL = "internal_get_interaction_date"
DATE_TASK_IDS = ["borrow_book#7", "borrow_book#9", "borrow_book#12", "borrow_book#20", "borrow_book#22",
                 "borrow_book#25", "reserve_room#4", "reserve_room#7"]


def test_ideal_agent_passes_every_executable_path_through_the_interaction_date_where_it_decides_the_label():
    tasks = [t for t in H.load_tasks("library") if t["id"] in DATE_TASK_IDS]
    paths = [(t, p) for t in tasks for p in executable_paths("library", t) if any(name == TOOL for name, _ in p)]
    results = H.run("library", [(t, ideal_calls(t, p)) for t, p in paths])
    assert len(results) == 8 and all(r["success"] for r in results)


def test_interaction_date_is_offered_where_it_decides_the_label():
    tasks = [t for t in H.load_tasks("library") if t["id"] in DATE_TASK_IDS]
    assert len(tasks) == 8 and all(TOOL in H.offered_tools("library", t) for t in tasks)


def test_asking_for_the_interaction_date_keeps_the_result_of_a_plan():
    tasks = H.load_tasks("library")
    plans = [(t, ideal_calls(t, p)) for t in tasks for p in executable_paths("library", t)]
    results = H.run("library", plans + [(t, calls + [H.Call(TOOL)]) for t, calls in plans])
    outcomes = [r["success"] for r in results]
    assert len(plans) == 78 and outcomes[:len(plans)] == outcomes[len(plans):]
    assert {t["id"] for (t, _), passed in zip(plans, outcomes) if passed} == {t["id"] for t in tasks}
