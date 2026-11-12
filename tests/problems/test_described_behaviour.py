import copy

import pytest

from env.variables import domain_assistant_keys, domain_keys
from tests import harness as H
from tests.labels import strict_system


def task(domain, task_id):
    return next(t for t in H.load_tasks(domain) if t["id"] == task_id)


def environment(domain, t):
    return domain_keys[domain](copy.deepcopy(t["initial_database"]),
                               domain_assistant_keys[domain].action_innate_dependencies, t["constraint_parameters"])


def tool(domain, name):
    return next(a for a in domain_assistant_keys[domain].actions if a["name"] == name)


def description(domain, name):
    return tool(domain, name)["description"]


@pytest.mark.parametrize("domain", ["bank", "dmv", "healthcare", "library", "online_market"])
def test_logout_can_return_false(domain):
    assert strict_system(domain, H.load_tasks(domain)[0]).logout_user("NO_SUCH_USER") is False
    assert "true always" not in description(domain, "logout_user")
    assert "or false if logout conditions are not met" in description(domain, "logout_user")


def test_enroll_course_in_the_environment_skips_prerequisites_and_availability():
    university = environment("university", task("university", "enroll_course#1"))
    assert university.enroll_course("alice", "CS201") is True
    assert "CS201" in university.students["alice"]["enrolled_courses"]
    assert "prerequisites" not in description("university", "enroll_course")
    assert "availability" not in description("university", "enroll_course")


def test_drop_course_in_the_environment_skips_the_deadline():
    university = environment("university", task("university", "drop_course#3"))
    assert university.drop_course("alice", "CS101") is True
    assert "deadline" not in description("university", "drop_course")


def test_course_check_reports_existence_not_availability():
    university = environment("university", task("university", "enroll_course#3"))
    assert university.internal_check_course_exists("CS201") == (True, True)
    assert university.internal_check_course_exists("NO_SUCH_COURSE") == (True, False)
    assert "availability" not in description("university", "internal_check_course_exists")
    assert "existence" in description("university", "internal_check_course_exists")


def test_check_in_does_not_require_the_day_of_arrival():
    t = task("hotel", "process_guest_checkin#0")
    assert t["initial_database"]["interaction_time"].split("T")[0] < t["user_known"]["check_in_date"]
    assert strict_system("hotel", t).process_guest_checkin(**t["user_known"])[0] is True
    assert "day of arrival" not in description("hotel", "process_guest_checkin")


def test_room_service_limit_counts_the_booking_record():
    t = task("hotel", "place_room_service_order#10")
    db = t["initial_database"]
    date = db["interaction_time"].split("T")[0]
    logged = [o for o in db["room_service_orders"].values() if o["room"] == "101" and o["order_time"].startswith(date)]
    assert len(logged) < t["constraint_parameters"]["max_room_service_orders_per_day"]
    tracker = strict_system("hotel", t).evaluation_get_state_tracker()
    assert tracker.within_room_service_order_daily_limit("John Doe", "101") is False
    for polarity in ["positive", "negative"]:
        text = getattr(domain_assistant_keys["hotel"], f"{polarity}_constraint_descriptions")[
            "within_room_service_order_daily_limit"]
        assert "\"room_service\" count" in text


def test_total_assets_do_not_decide_the_credit_card():
    assert environment("bank", task("bank", "apply_credit_card#6")).apply_credit_card("jane_doe", 0, 3000.0) is True
    parameter = tool("bank", "apply_credit_card")["parameters"]["properties"]["total_assets"]["description"]
    assert "eligibility" not in parameter


def test_get_loan_is_not_limited_by_the_maximum_loan_amount():
    bank = environment("bank", task("bank", "get_loan#0"))
    assert bank.get_bank_maximum_loan_amount() == (True, 0)
    assert bank.get_loan("jane_doe", 1000.0) is True
    assert "can loan" not in description("bank", "get_bank_maximum_loan_amount")
    assert "does not limit" in description("bank", "get_bank_maximum_loan_amount")


def test_inactive_is_not_offered_as_a_policy_type():
    t = task("healthcare", "reactivate_policy#5")
    assert strict_system("healthcare", t).evaluation_get_state_tracker().policy_type_valid("Inactive") is False
    for name in ["update_policy", "reactivate_policy"]:
        assert "Inactive" not in tool("healthcare", name)["parameters"]["properties"]["policy_type"]["description"]
