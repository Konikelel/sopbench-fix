"""Ablation add-ons for the SOP-compliance decomposition study.

Three information-only augmentations to the oracle setting, each toggled independently:
  - hint    : after each constraint, name the verification tool(s) that check it
              (from domain_assistant.constraint_processes).
  - verdict : after each *data* constraint, append its ground-truth satisfaction
              [SATISFIED]/[NOT SATISFIED], computed with the environment's own
              Dependency_Evaluator on the case's initial database + user_known.
              State-tracker / procedural constraints (login, auth) get no verdict.
  - order   : render the directed action graph into an explicit NL procedure.

None of these leak the final permissibility or force behavior.
"""
import re
from env.task import get_single_dep_verb
from env.variables import domain_assistant_keys


def _leaf_tools(cp_entry):
    """Extract the ordered, de-duplicated verification tool names from a
    constraint_processes entry (a dependency tuple, or None)."""
    if not cp_entry:
        return []
    if cp_entry[0] == "single":
        return [cp_entry[1]]
    out = []
    for d in cp_entry[1]:
        out += _leaf_tools(d)
    seen, res = set(), []
    for t in out:
        if t not in seen:
            seen.add(t)
            res.append(t)
    return res


def _hint_suffix(domain_str, cname):
    cp = domain_assistant_keys[domain_str].constraint_processes
    tools = _leaf_tools(cp.get(cname))
    if not tools:
        return ""
    return " (To verify this condition, call: " + " or ".join(f"`{t}`" for t in tools) + ".)"


def _verdict_suffix(domain_str, domain_system, dep_leaf, user_known):
    """Ground-truth verdict for a single constraint leaf. Only *data* constraints
    (fixed by the initial database) get a verdict. Procedural constraints whose
    state is changed by an action (login, authenticate) are listed in
    constraint_links; those are left to the agent to complete and get no verdict."""
    func = dep_leaf[1].replace("not ", "")
    cl = domain_assistant_keys[domain_str].constraint_links
    if func in cl:
        return ""  # procedural constraint (changed by an action) -> the agent performs it
    try:
        satisfied = bool(domain_system.domain_dep._process(dep_leaf, **user_known))
    except Exception:
        return ""  # cannot statically evaluate; leave to the agent
    return "  [SATISFIED]" if satisfied else "  [NOT SATISFIED]"


def annotated_structured(domain_str, dep, dep_params, domain_system, user_known,
                         hint=False, verdict=False, indent_level=0):
    """Same structured verbalization as env.task.dfsget_depverb_structured, but
    appends hint / verdict annotations to each single constraint leaf."""
    if not dep:
        return "None"
    if dep[0] == "single":
        base = get_single_dep_verb(domain_str, dep, dep_params)
        suffix = ""
        cname = dep[1].replace("not ", "")
        if hint:
            suffix += _hint_suffix(domain_str, cname)
        if verdict:
            suffix += _verdict_suffix(domain_str, domain_system, dep, user_known)
        return base + suffix
    parts = []
    if dep[0] == "and":
        parts.append("ALL of these conditions must be met:")
    elif dep[0] == "or":
        parts.append("ANY ONE of these conditions must be met:")
    elif dep[0] == "chain":
        parts.append("These steps must be completed in order:")
    for i, dep_part in enumerate(dep[1], 1):
        part_str = annotated_structured(domain_str, dep_part, dep_params, domain_system,
                                        user_known, hint, verdict, indent_level + 1)
        part_lines = part_str.split('\n')
        indent = "  " * indent_level
        if dep[0] == "chain":
            first_line = f"{indent}{i}. {part_lines[0]}"
        else:
            first_line = f"{indent}• {part_lines[0]}"
        parts.append('\n'.join([first_line] + part_lines[1:]))
    return '\n'.join(parts)


def render_order(dag):
    """Render a directed action graph into an explicit NL verification procedure.
    Leaves are literal tool names; operators map to ALL / ANY ONE / IN ORDER."""
    nodes, conns = dag["nodes"], dag["connections"]

    def children(idx):
        return [d for f, d in conns if f == idx]

    def walk(idx, depth):
        node = nodes[idx]
        ind = "  " * depth
        if isinstance(node, str):  # operator node
            label = {"and": "complete ALL of the following:",
                     "or": "complete ANY ONE of the following:",
                     "chain": "complete the following IN THIS ORDER:"}.get(node.lower(), node)
            lines = [f"{ind}{label}"]
            for c in children(idx):
                lines.append(walk(c, depth + 1))
            return "\n".join(lines)
        # (func, args) node
        fn = node[0]
        subs = children(idx)
        if not subs:
            return f"{ind}- call `{fn}`"
        # a function that itself has prerequisite verifications (e.g. the target service)
        lines = [f"{ind}- call `{fn}`, but first "]
        for c in subs:
            lines.append(walk(c, depth + 1))
        return "\n".join(lines)

    body = walk(0, 0)
    return ("### Required verification procedure for this request:\n"
            + body
            + "\nYou must complete the verification steps above before calling the target action.")
