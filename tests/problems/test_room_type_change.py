from tests import harness as H
from tests.agents import executable_paths, ideal_calls


def test_changing_the_room_type_frees_the_old_room_only_under_its_own_type():
    task = next(t for t in H.load_tasks("hotel") if t["id"] == "modify_reservation#0")
    assert task["initial_database"]["room_assignment"]["BK002"] == "108"
    entry, _ = H.simulate("hotel", task, ideal_calls(task, executable_paths("hotel", task)[0]))
    rooms = entry["interactions"][0]["database"]["rooms"]
    assert "108" not in rooms["suite"]["availability"]
    assert {"2024-12-03", "2024-12-04", "2024-12-05"} <= set(rooms["double"]["availability"]["108"])
