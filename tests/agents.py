import collections
import json

from tests import harness as H


def graph_paths(task):
    graph = task["directed_action_graph"]
    nodes = graph["nodes"]
    children = collections.defaultdict(list)
    for parent, child in graph["connections"]:
        children[parent].append(child)

    def walk(i):
        if nodes[i] == "or":
            return [p for c in children[i] for p in walk(c)]
        combined = [[]]
        for c in children[i]:
            combined = [a + b for a in combined for b in walk(c)]
        return combined if nodes[i] == "and" else [p + [tuple(nodes[i])] for p in combined]

    unique = {}
    for path in walk(0):
        steps = list({(name, json.dumps(mapping, sort_keys=True)): (name, mapping) for name, mapping in path}.values())
        unique.setdefault(json.dumps(steps, sort_keys=True), steps)
    return list(unique.values())


def arguments(task, mapping):
    known = task["user_known"]
    return {param: known[key] for param, key in mapping.items() if key in known}


def ideal_calls(task, path):
    return [H.Call(name, arguments(task, mapping)) for name, mapping in path
            if task["action_should_succeed"] or name != task["user_goal"]]


def executable_paths(domain, task):
    offered = set(H.offered_tools(domain, task))
    return [p for p in graph_paths(task) if all(c.name in offered for c in ideal_calls(task, p))]


def ideal_agent(domain, tasks):
    entries, owner = [], []
    for task in tasks:
        for path in executable_paths(domain, task):
            calls = ideal_calls(task, path)
            entry, offered = H.simulate(domain, task, calls)
            assert {c.name for c in calls} <= set(offered), task["id"]
            entries.append(entry)
            owner.append(task["id"])
    executable, passed = collections.Counter(owner), collections.Counter()
    for task_id, evaluation in zip(owner, H.evaluate(domain, entries) if entries else []):
        passed[task_id] += evaluation["success"]
    return {task["id"]: (passed[task["id"]], executable[task["id"]]) for task in tasks}


def idle_agent(domain, tasks):
    return {task["id"]: e["success"] for task, e in zip(tasks, H.run(domain, [(task, []) for task in tasks]))}
