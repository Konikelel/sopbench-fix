"""Scripted-model harness around the official simulation and evaluation code.

A scripted model stands in for the LLM inside run_simulation.run_task_simulation (the official
loop, user agent and limits as built by run_simulation.main), the results are written with
run_simulation.save_results, and they are scored by the unmodified run_evaluation.main reading
those files, so a change in SOPBench code shows up in every test and statistic that uses the harness.

run_simulation.main itself needs a model API, so three parts of it are mirrored here and must
follow it if it changes: loading the tasks file, the result entry it saves, and the output file name.
"""
import contextlib
import copy
import io
import json
import os
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from unittest import mock

import run_evaluation as RE
import run_simulation as RS
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall, Function
from env.task import task_initializer
from env.variables import domain_keys
from swarm.llm_handler import OpenAIHandler
from swarm.types import Agent
from swarm.util import construct_chatcompletion

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MODEL_NAME = "scripted"


def domains():
    """Domains in the order run_evaluation.py --domain all processes them."""
    return [d for d in domain_keys if "_strict" not in d]


@dataclass
class Call:
    """One tool call of the scripted model."""
    name: str
    arguments: dict = field(default_factory=dict)


class ScriptedModel(OpenAIHandler):
    """Model client that replays a fixed list of steps.

    A step is a Call, a list of Calls (parallel calls in one message) or a string (text reply).
    After the last step the model calls exit_conversation. The tool names offered in each request
    are recorded in `offered`. It subclasses OpenAIHandler only because Agent.client requires one.
    """

    def __init__(self, steps):
        self.model_name = MODEL_NAME
        self.model_name_huggingface = MODEL_NAME
        self.process = None
        self.steps = list(steps)
        self.offered = []

    def inference(self, create_params, debug, mode="chat", tool_call_mode="fc"):
        self.offered.append([t["function"]["name"] for t in create_params.get("tools", [])])
        step = self.steps.pop(0) if self.steps else Call(RS.exit_conversation.__name__)
        if isinstance(step, str):
            return {"completion": construct_chatcompletion("assistant", step)}
        calls = step if isinstance(step, list) else [step]
        tool_calls = [
            ChatCompletionMessageToolCall(
                id="call_" + uuid.uuid4().hex[:8], type="function",
                function=Function(name=c.name, arguments=json.dumps(c.arguments)))
            for c in calls
        ]
        return {"completion": construct_chatcompletion("assistant", None, tool_calls)}


def simulation_args(domain, *flags):
    """run_simulation.py arguments: CLI defaults plus `flags`."""
    with mock.patch.object(sys, "argv", ["run_simulation.py", "--domain", domain,
                                         "--assistant_model", MODEL_NAME, *flags]):
        return RS.parse_args()


def load_tasks(domain):
    """Tasks as run_simulation.main loads them, each with an `id` of the form goal#index."""
    args = simulation_args(domain)
    with open(os.path.join(ROOT, args.data_dir, f"{domain}_tasks.json"), encoding="utf-8") as f:
        tasks_dict = json.load(f)
    tasks = []
    for task_key in tasks_dict:
        for i, task in enumerate(copy.deepcopy(tasks_dict[task_key])):
            task["user_goal"] = task_key
            task["id"] = f"{task_key}#{i}"
            tasks.append(task)
    return tasks


_DEP_FULL = {}


def _dep_full(args):
    key = (args.domain, args.default_constraint_option, args.constraint_descr_format)
    if key not in _DEP_FULL:
        _DEP_FULL[key] = RS.task_default_dep_full(args.domain, args.default_constraint_option,
                                                  args.constraint_descr_format, dependency_verb_dep_orig=True)
    return _DEP_FULL[key]


def offered_tools(domain, task, *flags):
    """Names of the tools the simulation gives the agent for this task (exit_conversation excluded)."""
    args = simulation_args(domain, *flags)
    included = [node[0] for node in task["directed_action_graph"]["nodes"]] if args.tool_list == "oracle" else None
    _, _, assistant_info, _ = task_initializer(
        domain, copy.deepcopy(task), *_dep_full(args), included, args.env_mode, args.shuffle_func,
        args.constraint_descr_format, abl_hint=args.constraint_hint, abl_verdict=args.constraint_verdict,
        abl_order=args.action_order)
    return [t["function"]["name"] for t in assistant_info["tools"]]


def simulate(domain, task, steps, *flags):
    """One conversation in the official loop; returns (result entry as run_simulation.main saves it,
    tool names offered to the model in its first request)."""
    args = simulation_args(domain, *flags)
    task = copy.deepcopy(task)
    model = ScriptedModel(steps)
    assistant_agent = Agent(name="domain assistant", client=model, temperature=args.assistant_temperature,
                            top_p=args.assistant_top_p, max_tokens=args.assistant_max_tokens,
                            tool_call_mode=args.tool_call_mode, instructions="", functions=[])
    user_agent = Agent(name="user", client=None, default_response="", response_repeat=True)
    dep_innate_full, default_dep_full, default_dep_full_descr = _dep_full(args)
    with contextlib.redirect_stdout(io.StringIO()):
        result = RS.run_task_simulation(args=args, task=task, dep_innate_full=dep_innate_full,
                                        default_dep_full=default_dep_full,
                                        default_dep_full_descr=default_dep_full_descr,
                                        assistant_agent=assistant_agent, user_agent=user_agent)
    task["assistant_prompt"] = result["prompt"]
    for message in result["interaction"]:
        message.pop("role", None)
    entry = {
        "domain": args.domain,
        "setup": {
            "env_mode": args.env_mode,
            "shuffle_func": args.shuffle_func,
            "default_constraint_option": args.default_constraint_option,
            "constraint_descr_format": args.constraint_descr_format,
            "tool_list": args.tool_list,
            "user_agent": {
                "model": args.user_model,
                "temperature": args.user_temperature,
                "top_p": args.user_top_p,
                "max_tokens": args.user_max_tokens,
                "tool_call_mode": args.tool_call_mode,
            },
            "assistant_agent": {
                "model": args.assistant_model,
                "temperature": args.assistant_temperature,
                "top_p": args.assistant_top_p,
                "max_tokens": args.assistant_max_tokens,
                "tool_call_mode": args.tool_call_mode,
            },
        },
        "task": task,
        "interactions": [result],
    }
    return entry, (model.offered[0] if model.offered else [])


def _output_file(output_dir, args):
    name = (f"ast_{args.assistant_model}-mode_{args.tool_call_mode}-dep_{args.default_constraint_option}-"
            f"fmt_{args.constraint_descr_format}-tool_{args.tool_list}-shuffle_{args.shuffle_func}.json")
    return os.path.join(output_dir, args.domain, name)


def evaluate(domain, entries, *flags):
    """Score result entries of one domain with run_evaluation.main; returns one evaluation per entry."""
    args = simulation_args(domain, *flags)
    with tempfile.TemporaryDirectory() as output_dir:
        output_file = _output_file(output_dir, args)
        os.makedirs(os.path.dirname(output_file))
        RS.save_results(output_file, entries)
        argv = ["run_evaluation.py", "--assistant_model", args.assistant_model,
                "--tool_call_mode", args.tool_call_mode, "--tool_list", args.tool_list,
                "--default_constraint_option", args.default_constraint_option,
                "--constraint_descr_format", args.constraint_descr_format,
                "--domain", domain, "--output_dir", output_dir]
        if args.shuffle_func:
            argv.append("--shuffle_func")
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            RE.main()
        with open(output_file, encoding="utf-8") as f:
            scored = json.load(f)
    assert len(scored) == len(entries) and all("evaluations" in e for e in scored), "run_evaluation did not score the file"
    return [e["evaluations"][0] for e in scored]


def run(domain, runs, *flags):
    """Simulate and score (task, steps) pairs of one domain; returns one evaluation per pair."""
    if not runs:
        return []
    return evaluate(domain, [simulate(domain, task, steps, *flags)[0] for task, steps in runs], *flags)
