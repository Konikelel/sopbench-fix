import re

import pytest

from tests import harness as H

NESTED_HEADER = re.compile(r"( *)(?:•|\d+\.) (?:ALL of these|ANY ONE of these|These steps)")


def indent(line):
    return len(line) - len(line.lstrip(" "))


@pytest.mark.parametrize("flags", [(), ("--constraint_hint", "--constraint_verdict")])
def test_every_nesting_level_is_indented_deeper_than_its_header(flags):
    flattened, prompts_with_a_third_level = [], {}
    for domain in H.domains():
        prompts_with_a_third_level[domain] = 0
        for task in H.load_tasks(domain):
            lines = H.assistant_info(domain, task, flags)["instructions"].split("\n")
            headers = [(i, len(m.group(1))) for i, line in enumerate(lines) if (m := NESTED_HEADER.match(line))]
            if any(indent(lines[i + 1]) <= column for i, column in headers):
                flattened.append(f"{domain} {task['id']}")
            prompts_with_a_third_level[domain] += any(column > 0 for _, column in headers)
    assert prompts_with_a_third_level == {"bank": 0, "dmv": 91, "healthcare": 0, "library": 0,
                                          "online_market": 159, "hotel": 0, "university": 0}
    assert flattened == []
