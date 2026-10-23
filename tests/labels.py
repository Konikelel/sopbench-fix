import copy

from env.task import get_default_dep_full
from env.variables import domain_assistant_keys, domain_keys
from tests.agents import arguments, graph_paths


def strict_system(domain, task):
    default_dep_full = get_default_dep_full(domain, "full")
    default_dep_full[task["user_goal"]] = task["constraints"]
    return domain_keys[domain + "_strict"](copy.deepcopy(task["initial_database"]),
                                           domain_assistant_keys[domain].action_innate_dependencies,
                                           default_dep_full, task["constraint_parameters"])


def path_outcomes(domain, task):
    outcomes = set()
    for path in graph_paths(task):
        assert path[-1][0] == task["user_goal"], task["id"]
        system = strict_system(domain, task)
        for name, mapping in path:
            try:
                result = getattr(system, name)(**arguments(task, mapping))
            except Exception:
                result = False
        outcomes.add(bool(result[0] if isinstance(result, tuple) else result))
    return outcomes


def label_mismatches(domain, tasks):
    return [t["id"] for t in tasks if path_outcomes(domain, t) != {t["action_should_succeed"]}]
