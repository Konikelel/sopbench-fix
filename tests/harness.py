import contextlib
import copy
import io
import json
import os
import sys
import tempfile
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
    return [d for d in domain_keys if "_strict" not in d]


@dataclass
class Call:
    name: str
    arguments: dict = field(default_factory=dict)


class ScriptedModel(OpenAIHandler):
    def __init__(self, calls):
        self.model_name = self.model_name_huggingface = MODEL_NAME
        self.process = None
        self.calls = list(calls)
        self.offered = []

    def inference(self, create_params, debug, mode="chat", tool_call_mode="fc"):
        self.offered = [t["function"]["name"] for t in create_params["tools"]]
        message = self.calls.pop(0) if self.calls else Call(RS.exit_conversation.__name__)
        tool_calls = [ChatCompletionMessageToolCall(id=f"call_{len(self.calls)}_{i}", type="function",
                                                    function=Function(name=call.name, arguments=json.dumps(call.arguments)))
                      for i, call in enumerate(message if isinstance(message, list) else [message])]
        return {"completion": construct_chatcompletion("assistant", None, tool_calls)}


def simulation_args(domain):
    with mock.patch.object(sys, "argv", ["run_simulation.py", "--domain", domain, "--assistant_model", MODEL_NAME]):
        return RS.parse_args()


def load_tasks(domain):
    with open(os.path.join(ROOT, "data", f"{domain}_tasks.json"), encoding="utf-8") as f:
        tasks_dict = json.load(f)
    return [{**task, "user_goal": goal, "id": f"{goal}#{i}"}
            for goal, goal_tasks in tasks_dict.items() for i, task in enumerate(goal_tasks)]


def dep_full(args):
    return RS.task_default_dep_full(args.domain, args.default_constraint_option, args.constraint_descr_format,
                                    dependency_verb_dep_orig=True)


def offered_tools(domain, task):
    args = simulation_args(domain)
    _, _, assistant_info, _ = task_initializer(domain, copy.deepcopy(task), *dep_full(args), None, args.env_mode,
                                               args.shuffle_func, args.constraint_descr_format)
    return [t["function"]["name"] for t in assistant_info["tools"]]


def simulate(domain, task, calls):
    args = simulation_args(domain)
    task = copy.deepcopy(task)
    model = ScriptedModel(calls)
    assistant = Agent(name="domain assistant", client=model, temperature=args.assistant_temperature,
                      top_p=args.assistant_top_p, max_tokens=args.assistant_max_tokens,
                      tool_call_mode=args.tool_call_mode, instructions="", functions=[])
    user = Agent(name="user", client=None, default_response="", response_repeat=True)
    with contextlib.redirect_stdout(io.StringIO()):
        result = RS.run_task_simulation(args, task, *dep_full(args), assistant, user)
    task["assistant_prompt"] = result["prompt"]
    for message in result["interaction"]:
        message.pop("role", None)
    return {"domain": domain, "task": task, "interactions": [result]}, model.offered


def evaluate(domain, entries):
    with tempfile.TemporaryDirectory() as output_dir:
        output_file = os.path.join(output_dir, domain,
                                   f"ast_{MODEL_NAME}-mode_fc-dep_full-fmt_structured-tool_full-shuffle_False.json")
        os.makedirs(os.path.dirname(output_file))
        RS.save_results(output_file, entries)
        argv = ["run_evaluation.py", "--assistant_model", MODEL_NAME, "--tool_list", "full",
                "--domain", domain, "--output_dir", output_dir]
        with mock.patch.object(sys, "argv", argv), contextlib.redirect_stdout(io.StringIO()), \
                contextlib.redirect_stderr(io.StringIO()):
            RE.main()
        with open(output_file, encoding="utf-8") as f:
            scored = json.load(f)
    assert len(scored) == len(entries) and all("evaluations" in e for e in scored)
    return [e["evaluations"][0] for e in scored]


def run(domain, runs):
    return evaluate(domain, [simulate(domain, task, calls)[0] for task, calls in runs]) if runs else []
