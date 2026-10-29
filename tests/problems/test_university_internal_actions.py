import pytest

from env.domains.university.university import University, University_Strict
from tests import harness as H


def tools(cls):
    return {name for name in dir(cls) if not name.startswith(("_", "evaluation_"))}


def evaluate_student_info_call(arguments):
    task = next(t for t in H.load_tasks("university") if t["id"] == "declare_minor#0")
    login = H.Call("login_user", {k: task["user_known"][k] for k in ("username", "password")})
    entry, _ = H.simulate("university", task, [login, H.Call("internal_get_student_info")])
    [call] = [c for m in entry["interactions"][0]["interaction"] for c in m.get("tool_calls") or []
              if c["function"]["name"] == "internal_get_student_info"]
    call["function"]["arguments"] = arguments
    return H.evaluate("university", [entry])[0]


def test_strict_system_has_every_university_tool():
    assert tools(University) == tools(University_Strict)


@pytest.mark.parametrize("arguments", ["{}", "[1]", "null", '"x"'])
def test_invalid_internal_action_arguments_are_a_tool_call_error(arguments):
    assert not evaluate_student_info_call(arguments)["no_tool_call_error"]
