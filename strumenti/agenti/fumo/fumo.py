"""Fumo: can we tell early, from outside the model, that a coding-agent run will fail? (PIANO_FUMO.md)

Four agents, four viewpoints, one baseline. Only what a host can see: the sequence of tool calls, whether each
result was an error, how long it was, and the text the agent wrote. No weights, no hidden states.
  python fumo.py estrai     reads the trajectories once and writes compact step lists (fumo_passi.jsonl)
  python fumo.py lunghezze  run lengths per agent, without outcomes (to set the checkpoint before any scoring)
  python fumo.py valuta     features at the checkpoint, leave-one-agent-out evaluation, summary
"""
import collections
import glob
import hashlib
import json
import math
import os
import random
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "modifiche")))
import formati  # noqa: E402

ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
EXT = os.path.join(ROOT, "esterni")
OUT = os.path.join(ROOT, "strumenti", "risultati", "fumo")
STEPS = os.path.join(OUT, "fumo_passi.jsonl")
SEED = "fumo-2026-10-15"
AGENTS = {
    "qwen3_coder_30b": ("openhands", "20250805-openhands-Qwen3-Coder-30B-A3B-Instruct",
                        "20250805_openhands-Qwen3-Coder-30B-A3B-Instruct"),
    "qwen3_coder_480b": ("openhands", "20250805-openhands-Qwen3-Coder-480B-A35B-Instruct",
                         "20250805_openhands-Qwen3-Coder-480B-A35B-Instruct"),
    "claude_opus_4_5": ("observations", "20251127_openhands_claude-opus-4-5", "20251127_openhands_claude-opus-4-5"),
    "gemma4_e4b": ("gemma", os.path.join(ROOT, "strumenti", "risultati", "grafi", "agente_test"), None),
}
EXIT = re.compile(r"exit code (-?\d+)")
SEARCH_CMD = re.compile(r"^\s*(cd [^;&]+(&&|;)\s*)?(grep|rg|find|ls|tree|git (grep|log|show|diff|status))\b")
READ_CMD = re.compile(r"^\s*(cd [^;&]+(&&|;)\s*)?(cat|head|tail|sed -n|nl|less|more|awk)\b")
EMPTY_JSON_LIST = re.compile(r'":\s*\[\]')
PREAMBLE = re.compile(r"^\s*(source \S+ && )?(conda activate \S+ && )?(cd \S+ && )?")
TEXT_ERROR = re.compile(r"Traceback \(most recent call last\)|\bFAILED\b|\bERROR\b|Error:|command not found|"
                        r"No such file or directory|SyntaxError|failed with code [1-9]|exit code [1-9]")


def h(*parts):
    return hashlib.sha1("\x1f".join(str(p) for p in parts).encode("utf-8", "replace")).hexdigest()[:12]


def step(kind, key, error, text, said=None):
    return {"t": kind, "k": key, "e": int(bool(error)), "n": len(text or ""), "a": (said or "")[:600] or None}


# ---------- one step per tool call ----------

def openhands_step(name, args, result, said):
    try:
        a = json.loads(args) if isinstance(args, str) else (args or {})
    except ValueError:
        a = {}
    a = a if isinstance(a, dict) else {}
    if name == "str_replace_editor":
        cmd = a.get("command")
        kind = "read" if cmd == "view" else "edit" if cmd in ("create", "str_replace", "insert", "undo_edit") else "other"
        key = h(name, cmd, a.get("path"), a.get("view_range"), a.get("old_str"), a.get("new_str"), a.get("file_text"))
        error = formati.editor_outcome(result) in ("noop", "missing", "multiple", "other_error")
        return step(kind, key, error, result, said)
    if name == "execute_bash":
        cmd = " ".join(str(a.get("command") or "").split())
        kind = "search" if SEARCH_CMD.match(cmd) else "read" if READ_CMD.match(cmd) else "run"
        codes = EXIT.findall(result or "")
        return step(kind, h(name, cmd), bool(codes) and codes[-1] != "0", result, said)
    return step("other", h(name, json.dumps(a, sort_keys=True)), False, result, said)


def openhands_runs(agent, trajs, results):
    outcomes = formati.load_outcomes(os.path.join(EXT, "swebench-results", results, "results.json"))
    for run in formati.openhands_events(os.path.join(EXT, "swebench-trajs", trajs), outcomes):
        msgs, steps, said = run["messages"] or [], [], None
        for i, m in enumerate(msgs):
            if m.get("role") == "assistant":
                said = m.get("content")
                for c in m.get("tool_calls") or []:
                    nxt = msgs[i + 1] if i + 1 < len(msgs) and msgs[i + 1].get("role") == "tool" else {}
                    steps.append(openhands_step(c["function"]["name"], c["function"].get("arguments"),
                                                nxt.get("content") or "", said if not (m.get("meta") or {}).get("shared_response") else None))
            elif m.get("role") == "error":
                steps.append(step("other", h("error", m.get("content")), True, m.get("content"), None))
        yield {"agent": agent, "id": run["id"], "task": run["task"], "outcome": run["outcome"], "steps": steps}


def observation_runs(agent, trajs, results):
    outcomes = formati.load_outcomes(os.path.join(EXT, "swebench-results", results, "results.json"))
    for run in formati.observation_logs(os.path.join(EXT, "swebench-trajs", trajs), outcomes):
        steps = []
        for tool, text in run["observations"] or []:
            if tool in ("str_replace_editor", "file_editor"):
                eo = formati.editor_outcome(text)
                kind = "read" if eo == "view" else "edit" if eo in ("edited", "created", "undo", "noop", "missing", "multiple") else "other"
                error = eo in ("noop", "missing", "multiple", "other_error")
            elif tool in ("execute_bash", "terminal"):
                # these logs keep no call and no exit-code line: the command is echoed at the start of the text
                first = PREAMBLE.sub("", (text or "").split("\n", 1)[0])
                kind = "search" if SEARCH_CMD.match(first) else "read" if READ_CMD.match(first) else "run"
                codes = EXIT.findall(text or "")
                error = (codes[-1] != "0") if codes else bool(TEXT_ERROR.search((text or "")[-2000:]))
            else:
                kind, error = "other", False
            steps.append(step(kind, h(tool, (text or "")[:3000]), error, text, None))
        yield {"agent": agent, "id": run["id"], "task": run["task"], "outcome": run["outcome"], "steps": steps}


GEMMA_KIND = {"read_file": "read", "search_code": "search", "list_files": "search", "search_similar_code": "search",
              "get_code_neighbors": "search", "get_code_subgraph": "search", "submit_locations": "other"}


def gemma_runs(agent, folder, _):
    import ast as _ast
    for f in sorted(glob.glob(os.path.join(folder, "*.json"))):
        if ".infra_" in os.path.basename(f):
            continue
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        if not r.get("gold_defs"):
            continue                      # no definition to find: the outcome is undefined
        msgs, steps = r["messages"], []
        for i, m in enumerate(msgs):
            if m.get("role") != "assistant" or not m.get("tool_calls"):
                continue
            calls = m["tool_calls"]
            if isinstance(calls, str):
                try:
                    calls = _ast.literal_eval(calls)
                except (ValueError, SyntaxError):
                    calls = []
            for c in calls:
                fn = c.get("function") or {}
                nxt = msgs[i + 1] if i + 1 < len(msgs) and msgs[i + 1].get("role") == "tool" else {}
                text = nxt.get("content") or ""
                error = '"status": "error"' in text or bool(EMPTY_JSON_LIST.search(text[:400]))
                steps.append(step(GEMMA_KIND.get(fn.get("name"), "other"),
                                  h(fn.get("name"), json.dumps(fn.get("arguments"), sort_keys=True)), error, text,
                                  m.get("content")))
        yield {"agent": agent, "id": f"{r['task']}_{r['condition']}", "task": r["task"],
               "outcome": "resolved" if r["hit"]["fn_exact"] else "unresolved", "steps": steps}


def extract():
    os.makedirs(OUT, exist_ok=True)
    readers = {"openhands": openhands_runs, "observations": observation_runs, "gemma": gemma_runs}
    counts = collections.Counter()
    with open(STEPS, "w", encoding="utf-8") as out:
        for agent, (kind, a, b) in AGENTS.items():
            for run in readers[kind](agent, a, b):
                out.write(json.dumps(run, ensure_ascii=False) + "\n")
                counts[agent] += 1
            print(agent, counts[agent], flush=True)
    print(dict(counts))


def load():
    with open(STEPS, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh]


def lengths():
    """Run lengths per agent WITHOUT outcomes: used only to fix the checkpoint before any scoring."""
    by = collections.defaultdict(list)
    for r in load():
        by[r["agent"]].append(len(r["steps"]))
    for agent, xs in by.items():
        xs.sort()
        q = lambda p: xs[min(len(xs) - 1, int(p * len(xs)))]
        print(agent, "runs", len(xs), "min", xs[0], "median", q(0.5), "p90", q(0.9), "p99", q(0.99), "max", xs[-1])


if __name__ == "__main__":
    {"estrai": extract, "lunghezze": lengths}[sys.argv[1]]()
