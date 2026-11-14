import re

from tests import harness as H

LICENSE = re.compile(r"driver.?s?.?licen[cs]e", re.I)


def password_called_license():
    return [(domain, task["id"]) for domain in ("bank", "healthcare") for task in H.load_tasks(domain)
            if isinstance(task["user_known"].get("identification"), str) and LICENSE.search(task["user_prompt"])]


def test_password_is_not_called_a_drivers_license():
    assert password_called_license() == []
