import ast
import collections
import json

from env import evaluator
from env.variables import domain_assistant_keys
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


def responses(entry):
    return [m["content"] for m in entry["interactions"][0]["interaction"] if "tool_call_id" in m]


def response_value(response):
    try:
        return ast.literal_eval(response)
    except (ValueError, SyntaxError):
        return None


def ideal_plan(domain, task, path):
    calls = ideal_calls(task, path)
    for i, (call, (_, mapping)) in enumerate(zip(calls, path)):
        missing = mapping.keys() - call.arguments.keys()
        if missing:
            earlier = map(response_value, responses(H.simulate(domain, task, calls[:i])[0]))
            call.arguments.update({k: r[k] for r in earlier if isinstance(r, dict) for k in missing if k in r})
    if (not task["action_should_succeed"] and hasattr(evaluator, "gather_violated_deps")
            and not evaluator.gather_violated_deps(domain, task, "full")[1]):
        calls.append(H.Call(task["user_goal"], arguments(task, path[-1][1])))
    entry, offered = H.simulate(domain, task, calls)
    if task["action_should_succeed"]:
        return calls, entry, offered
    gates = {action for action, _ in domain_assistant_keys[domain].constraint_links.values()}
    failed = next((i for i, (c, r) in enumerate(zip(calls, responses(entry))) if c.name in gates and r == "False"), None)
    if failed is None or failed == len(calls) - 1:
        return calls, entry, offered
    calls = calls[:failed + 1]
    return (calls, *H.simulate(domain, task, calls))


def ideal_agent(domain, tasks):
    entries, owner = [], []
    for task in tasks:
        for path in executable_paths(domain, task):
            calls, entry, offered = ideal_plan(domain, task, path)
            assert {c.name for c in calls} <= set(offered), task["id"]
            entries.append(entry)
            owner.append(task["id"])
    executable, passed = collections.Counter(owner), collections.Counter()
    for task_id, evaluation in zip(owner, H.evaluate(domain, entries) if entries else []):
        passed[task_id] += evaluation["success"]
    return {task["id"]: (passed[task["id"]], executable[task["id"]]) for task in tasks}


def idle_agent(domain, tasks):
    return {task["id"]: e["success"] for task, e in zip(tasks, H.run(domain, [(task, []) for task in tasks]))}
