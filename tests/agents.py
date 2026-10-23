"""The ideal agent and the idle agent, run through the harness.

Ideal agent: in every task it walks each path through the task's directed action graph that uses
only tools the simulation offers the agent, with arguments taken from user_known. On a task that
should succeed it ends the path with the target action; on a task that should fail it walks the
path without the target action and exits. A task counts as passed when it has at least one such
path and every such path passes the official evaluation.

Idle agent: ends the conversation without any action.
"""
import collections
import json
from dataclasses import dataclass

from tests import harness as H


def graph_paths(task):
    """Every path through the task's directed action graph, as lists of (action, parameter mapping).

    An "or" node contributes each child's paths as alternatives, an "and" node concatenates its
    children's paths in the order of the graph's connections, and an action node comes after the
    paths of its prerequisites. A step repeated within a path is kept at its first position, and
    identical paths are listed once.
    """
    graph = task["directed_action_graph"]
    nodes = graph["nodes"]
    children = {i: [] for i in range(len(nodes))}
    for parent, child in graph["connections"]:
        children[parent].append(child)

    def walk(i):
        if isinstance(nodes[i], str):
            alternatives = [walk(c) for c in children[i]]
            if nodes[i] == "or":
                return [p for paths in alternatives for p in paths]
            combined = [[]]
            for paths in alternatives:
                combined = [a + b for a in combined for b in paths]
            return combined
        before = [[]]
        for c in children[i]:
            before = [a + b for a in before for b in walk(c)]
        return [p + [(nodes[i][0], nodes[i][1])] for p in before]

    unique, seen_paths = [], set()
    for path in walk(0):
        steps, seen_steps = [], set()
        for name, mapping in path:
            key = (name, json.dumps(mapping, sort_keys=True))
            if key not in seen_steps:
                seen_steps.add(key)
                steps.append((name, mapping))
        key = json.dumps(steps, sort_keys=True)
        if key not in seen_paths:
            seen_paths.add(key)
            unique.append(steps)
    return unique


def arguments(task, mapping):
    """Call arguments for a graph parameter mapping; parameters missing from user_known are left out."""
    known = task["user_known"]
    return {param: known[key] for param, key in mapping.items() if key in known}


def ideal_calls(task, path):
    """The ideal agent's calls on one path."""
    return [H.Call(name, arguments(task, mapping)) for name, mapping in path
            if task["action_should_succeed"] or name != task["user_goal"]]


def executable_paths(domain, task):
    """Graph paths on which every call of the ideal agent goes to a tool offered to the agent."""
    offered = set(H.offered_tools(domain, task))
    return [p for p in graph_paths(task) if all(c.name in offered for c in ideal_calls(task, p))]


@dataclass
class IdealResult:
    task_id: str
    executable: int
    passed: int

    @property
    def task_passed(self):
        return self.executable > 0 and self.passed == self.executable


def ideal_agent(domain, tasks=None):
    """IdealResult per task of the domain."""
    tasks = H.load_tasks(domain) if tasks is None else tasks
    entries, owner = [], []
    for task in tasks:
        for path in executable_paths(domain, task):
            calls = ideal_calls(task, path)
            entry, offered = H.simulate(domain, task, calls)
            assert {c.name for c in calls} <= set(offered), f"{task['id']}: a call goes to a tool the model was not offered"
            entries.append(entry)
            owner.append(task["id"])
    executable, passed = collections.Counter(owner), collections.Counter()
    for task_id, evaluation in zip(owner, H.evaluate(domain, entries) if entries else []):
        passed[task_id] += bool(evaluation["success"])
    return [IdealResult(task["id"], executable[task["id"]], passed[task["id"]]) for task in tasks]


def idle_agent(domain, tasks=None):
    """{task id: success} of the idle agent."""
    tasks = H.load_tasks(domain) if tasks is None else tasks
    evaluations = H.run(domain, [(task, []) for task in tasks])
    return {task["id"]: bool(e["success"]) for task, e in zip(tasks, evaluations)}
