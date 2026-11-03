import ast
import collections
import copy
import itertools
import json

from env import evaluator
from env.helpers import dfsgather_ifg_func
from env.variables import domain_assistant_keys, domain_keys
from tests import harness as H


def graph_paths(task, graph=None):
    graph = graph or task["directed_action_graph"]
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


def dep_graph(domain, task, dep):
    if not dep or dep == task["constraints_original"]:
        return None
    system = domain_keys[domain](copy.deepcopy(task["initial_database"]), domain_assistant_keys[domain].action_innate_dependencies,
                                 task["constraint_parameters"])
    return dfsgather_ifg_func(system, domain_assistant_keys[domain], task["user_goal"], "full", False, dep)


def step_key(step):
    return json.dumps(step, sort_keys=True)


def step_keys(path):
    return {step_key(step) for step in path[:-1]}


def reactive_paths(raw, complete):
    checked = {step_key(step) for path in complete for step in path}
    raw_keys = [[step_key(step) for step in path] for path in raw]
    raw_sets = list(map(set, raw_keys))
    blocks = []
    for path, keys in zip(raw, raw_keys):
        unsatisfied = [i for i, k in enumerate(keys) if k not in checked]
        if unsatisfied:
            block = set(keys) - checked
            rank = max(min(i for i, k in enumerate(other) if k in block) for other, other_set in zip(raw_keys, raw_sets) if block <= other_set)
            blocks.append((block, set(keys) & checked, path[:unsatisfied[-1] + 1], set(keys[:unsatisfied[-1] + 1]), rank))
    parts = {id(entry): [other for other, *_ in blocks if other < entry[0]] for entry in blocks}
    blocks = [entry for entry in blocks if not any(not (a <= b or b <= a) for a, b in itertools.combinations(parts[id(entry)], 2))]

    def alternatives(a, b):
        return a != b and not any(a | b <= keys for keys in raw_sets)

    def sequences(chosen, rest):
        yield chosen
        for i, entry in enumerate(rest):
            if all(alternatives(entry[0], other[0]) for other in chosen):
                yield from sequences(chosen + [entry], rest[:i] + rest[i + 1:])

    paths = {}
    for path in complete:
        keys = [step_key(step) for step in path]
        groups = []
        for block, shared, prefix, prefix_keys, rank in blocks:
            if shared <= set(keys):
                entry = (block, prefix, min(i for i, k in enumerate(keys) if k not in prefix_keys), rank)
                group = next((group for group in groups if all(block == other or alternatives(block, other) for other, *_ in group)), None)
                groups.append([entry]) if group is None else group.append(entry)
        groups.sort(key=lambda group: max(rank for *_, rank in group))
        for choice in itertools.product(*(list(sequences([], group)) for group in groups)):
            inserts = collections.defaultdict(list)
            for _, prefix, position, _ in [entry for sequence in choice for entry in sequence]:
                inserts[position].extend(prefix)
            merged = list({step_key(s): s for i, step in enumerate(path) for s in inserts[i] + [step]}.values())
            if merged != path:
                paths.setdefault(step_key(merged), merged)
    return list(paths.values())


def branch_orders(dep, violated):
    if not dep or dep[0] == "single":
        return [dep]
    combined = itertools.product(*(branch_orders(part, violated) for part in dep[1]))
    if dep[0] in ("or", "gate") and violated(dep):
        return [[dep[0], list(order)] for parts in combined for order in itertools.permutations(parts)]
    return [[dep[0], list(parts)] for parts in combined]


def permuted_deps(domain, task):
    _, dep_eval = evaluator.gather_strict_dep_eval(domain, task, "full")
    constr_deps = domain_assistant_keys[domain].constraint_dependencies

    def violated(dep):
        return evaluator.dfsgather_violated_dep(dep, dep_eval, constr_deps, task["user_known"])

    deps = [evaluator.dfsgather_checked_dep(dep, dep_eval, constr_deps, task["user_known"])
            for dep in branch_orders(task["constraints_original"], violated)]
    return deps[1:]


def prefix_paths(domain, task):
    if not hasattr(evaluator, "gather_checked_dep"):
        return graph_paths(task)
    complete = graph_paths(task, dep_graph(domain, task, evaluator.gather_checked_dep(domain, task, "full")))
    violated = None if task["action_should_succeed"] else evaluator.gather_violated_deps(domain, task, "full")[1]
    if violated:
        complete += [p for dep in permuted_deps(domain, task) for p in graph_paths(task, dep_graph(domain, task, dep))]
    reactive = reactive_paths(graph_paths(task), complete)
    if not violated:
        return complete + reactive
    minimal = [step_keys(p) for p in graph_paths(task, dep_graph(domain, task, violated))]
    checked = {k for p in complete for k in step_keys(p)}
    paths = {}
    for path in complete + reactive:
        keys = [step_key(step) for step in path[:-1]]
        ends = [max((keys.index(k) for k in m), default=-1) for m in minimal if m <= set(keys)]
        if ends and (path in complete or not set(keys[:min(ends) + 1]) <= checked):
            prefix = path[:min(ends) + 1] + path[-1:]
            paths.setdefault(step_key(prefix), prefix)
    return list(paths.values())


def executable_paths(domain, task):
    offered = set(H.offered_tools(domain, task))
    executed = {}
    for path in prefix_paths(domain, task):
        if all(c.name in offered for c in ideal_calls(task, path)) and filled_calls(domain, task, path) is not None:
            calls = ideal_plan(domain, task, path)[0]
            executed.setdefault(json.dumps([[c.name, c.arguments] for c in calls], sort_keys=True), path)
    return list(executed.values())


def responses(entry):
    return [m["content"] for m in entry["interactions"][0]["interaction"] if "tool_call_id" in m]


def response_value(response):
    try:
        return ast.literal_eval(response)
    except (ValueError, SyntaxError):
        return None


def gates(domain):
    return {action for action, _ in domain_assistant_keys[domain].constraint_links.values()}


def filled_calls(domain, task, path):
    calls = ideal_calls(task, path)
    for i, (call, (_, mapping)) in enumerate(zip(calls, path)):
        missing = mapping.keys() - call.arguments.keys()
        if not missing:
            continue
        earlier = responses(H.simulate(domain, task, calls[:i])[0])
        call.arguments.update({k: r[k] for r in map(response_value, earlier) if isinstance(r, dict) for k in missing if k in r})
        if missing - call.arguments.keys():
            authenticated = any(c.name in gates(domain) and r == "True" for c, r in zip(calls[:i], earlier))
            if task["action_should_succeed"] or call.name not in gates(domain) or authenticated:
                return None
            return calls[:i + 1]
    return calls


def ideal_plan(domain, task, path):
    calls = filled_calls(domain, task, path)
    if (not task["action_should_succeed"] and hasattr(evaluator, "gather_violated_deps")
            and not evaluator.gather_violated_deps(domain, task, "full")[1]):
        calls.append(H.Call(task["user_goal"], arguments(task, path[-1][1])))
    entry, offered = H.simulate(domain, task, calls)
    if task["action_should_succeed"]:
        return calls, entry, offered
    failed = next((i for i, (c, r) in enumerate(zip(calls, responses(entry))) if c.name in gates(domain) and r == "False"), None)
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
