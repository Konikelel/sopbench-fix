import copy

import pytest

from env.variables import domain_assistant_keys, domain_keys
from tests import harness as H


@pytest.mark.parametrize("action, arguments", [
    ("process_guest_checkout", {"key_returned": True}),
    ("request_room_change", {"amount": 60.0, "reason": "upgrade", "room_type": "double"}),
])
def test_guest_without_a_booking_gets_false(action, arguments):
    task = next(t for t in H.load_tasks("hotel") if t["user_goal"] == action)
    system = domain_keys["hotel"](copy.deepcopy(task["initial_database"]),
                                  domain_assistant_keys["hotel"].action_innate_dependencies, task["constraint_parameters"])
    assert getattr(system, action)(guest_name="Nobody Here", **arguments) is False
