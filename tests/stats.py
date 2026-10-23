"""Benchmark statistics of the current code, per domain, as a Markdown table.

    python -m tests.stats [domain ...]

Ideal agent: tasks passed, and paths passed / executable paths (see tests/agents.py).
Idle agent: tasks passed. Label mismatches: tasks whose label disagrees with Strict (see tests/labels.py).
"""
import sys

from tests import harness as H
from tests.agents import ideal_agent, idle_agent
from tests.labels import label_mismatches


def domain_stats(domain):
    tasks = H.load_tasks(domain)
    ideal = ideal_agent(domain, tasks)
    return {
        "tasks": len(tasks),
        "ideal_tasks": sum(r.task_passed for r in ideal),
        "ideal_paths": sum(r.passed for r in ideal),
        "executable_paths": sum(r.executable for r in ideal),
        "idle": sum(idle_agent(domain, tasks).values()),
        "label_mismatches": len(label_mismatches(domain, tasks)),
    }


def row(name, s):
    return (f"| {name} | {s['ideal_tasks']}/{s['tasks']} | {s['ideal_paths']}/{s['executable_paths']} "
            f"| {s['idle']}/{s['tasks']} | {s['label_mismatches']} |")


def main(argv):
    names = argv or H.domains()
    stats = {d: domain_stats(d) for d in names}
    total = {k: sum(s[k] for s in stats.values()) for k in next(iter(stats.values()))}
    lines = ["| Domain | Ideal agent: tasks | Ideal agent: paths passed / executable | Idle agent | Label mismatches |",
             "|---|---|---|---|---|"]
    lines += [row(d, s) for d, s in stats.items()]
    lines.append(row("**all**", total))
    lines += ["", f"Ideal agent {total['ideal_tasks']}/{total['tasks']} tasks "
                  f"({total['ideal_paths']}/{total['executable_paths']} paths), "
                  f"idle agent {total['idle']}/{total['tasks']}, label mismatches {total['label_mismatches']}."]
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1:])
