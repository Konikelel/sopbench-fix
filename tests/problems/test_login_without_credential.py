import pytest

from tests import harness as H


def unknown_credential_tasks(domain):
    tasks = []
    for t in H.load_tasks(domain):
        logins = [n[1] for n in t["directed_action_graph"]["nodes"] if not isinstance(n, str) and n[0] == "login_user"]
        if logins and "username" in t["user_known"] and not t["action_should_succeed"] \
                and not any(key in t["user_known"] for param, key in logins[0].items() if param != "username"):
            tasks.append(t)
    return tasks


@pytest.mark.parametrize("domain, count", [("bank", 11), ("dmv", 2), ("healthcare", 1), ("library", 2),
                                           ("online_market", 1)])
def test_login_attempt_without_credential_then_refusal_passes(domain, count):
    tasks = unknown_credential_tasks(domain)
    runs = H.run(domain, [(t, [H.Call("login_user", {"username": t["user_known"]["username"]})]) for t in tasks])
    assert len(tasks) == count and all(r["success"] for r in runs)
