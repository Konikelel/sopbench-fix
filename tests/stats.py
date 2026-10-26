import sys

from tests import harness as H
from tests.agents import ideal_agent, idle_agent
from tests.labels import label_mismatches

KEYS = ["tasks", "ideal_any", "ideal_all", "ideal_paths", "executable_paths", "idle", "label_mismatches"]


def domain_stats(domain):
    tasks = H.load_tasks(domain)
    ideal = ideal_agent(domain, tasks).values()
    return {
        "tasks": len(tasks),
        "ideal_any": sum(passed > 0 for passed, _ in ideal),
        "ideal_all": sum(0 < passed == executable for passed, executable in ideal),
        "ideal_paths": sum(passed for passed, _ in ideal),
        "executable_paths": sum(executable for _, executable in ideal),
        "idle": sum(idle_agent(domain, tasks).values()),
        "label_mismatches": len(label_mismatches(domain, tasks)),
    }


def row(name, s):
    return (f"| {name} | {s['ideal_any']}/{s['tasks']} | {s['ideal_all']}/{s['tasks']} "
            f"| {s['ideal_paths']}/{s['executable_paths']} | {s['idle']}/{s['tasks']} | {s['label_mismatches']} |")


def main(names):
    stats = {d: domain_stats(d) for d in names or H.domains()}
    total = {k: sum(s[k] for s in stats.values()) for k in KEYS}
    print("| Domain | Ideal agent: tasks on any path | Ideal agent: tasks on all paths "
          "| Ideal agent: paths passed / executable | Idle agent | Label mismatches |")
    print("|---|---|---|---|---|---|")
    for d, s in stats.items():
        print(row(d, s))
    print(row("**all**", total))
    print(f"\nIdeal agent {total['ideal_any']}/{total['tasks']} tasks on any path, "
          f"{total['ideal_all']}/{total['tasks']} on all paths ({total['ideal_paths']}/{total['executable_paths']} paths), "
          f"idle agent {total['idle']}/{total['tasks']}, label mismatches {total['label_mismatches']}.")


if __name__ == "__main__":
    main(sys.argv[1:])
