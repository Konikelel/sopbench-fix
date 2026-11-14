import re

from tests import harness as H

CREDENTIALS = {"password", "identification"}


def punctuated_credentials(task):
    known = {v for k, v in task["user_known"].items() if k in CREDENTIALS and isinstance(v, str)}
    return [quoted for quoted in re.findall(r'"([^"]*)"', task["user_prompt"])
            if quoted not in known and quoted.rstrip(".,;:!?") in known]


def test_first_user_message_quotes_credentials_without_sentence_punctuation():
    found = {(domain, task["id"]): quoted for domain in H.domains() for task in H.load_tasks(domain)
             if (quoted := punctuated_credentials(task))}
    assert found == {}
