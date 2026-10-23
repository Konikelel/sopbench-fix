"""Label consistency: does action_should_succeed agree with the Strict system?

Every path through the task's directed action graph is replayed in the domain's Strict system,
built the way the evaluator builds it, with arguments from user_known. The outcome of a path is
the success flag of the target action's call (a call that raises counts as failed). A label is
consistent when every path ends with the outcome the label states.
"""
import copy

from env.task import get_default_dep_full
from env.variables import domain_assistant_keys, domain_keys
from tests import harness as H
from tests.agents import arguments, graph_paths


def strict_system(domain, task):
    default_dep_full = get_default_dep_full(domain, "full")
    default_dep_full[task["user_goal"]] = task["constraints"]
    return domain_keys[domain + "_strict"](copy.deepcopy(task["initial_database"]),
                                           domain_assistant_keys[domain].action_innate_dependencies,
                                           default_dep_full, task["constraint_parameters"])


def _succeeded(result):
    return bool(result[0]) if isinstance(result, tuple) else bool(result)


def path_outcomes(domain, task):
    """Set of target-action outcomes over all graph paths."""
    outcomes = set()
    for path in graph_paths(task):
        system = strict_system(domain, task)
        outcome = False
        for name, mapping in path:
            try:
                result = getattr(system, name)(**arguments(task, mapping))
            except Exception:
                result = False
            if name == task["user_goal"]:
                outcome = _succeeded(result)
        outcomes.add(outcome)
    return outcomes


def label_mismatches(domain, tasks=None):
    """Ids of the domain's tasks whose label is not consistent."""
    tasks = H.load_tasks(domain) if tasks is None else tasks
    return [t["id"] for t in tasks if path_outcomes(domain, t) != {bool(t["action_should_succeed"])}]
