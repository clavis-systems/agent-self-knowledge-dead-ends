"""Il senso costruito al bisogno (PIANO_SENSO.md): from the specification only, Gemma writes property checks;
the checks run against every "done" solution in the WASM sandbox.
  python senso.py scrivi     GPU: one check_properties(candidate) per task (proprieta.jsonl)
  python senso.py prova      CPU + WASM sandbox: run the checks on the 507 visible-pass solutions (esiti.jsonl)
  python senso.py valuta     gate decision and comparison with the fresh-look judge
"""
import ast
import json
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "sguardo")))
import sguardo as sg  # noqa: E402  (brings mercato, agente_gemma, the WASM sandbox and the AUC)

mk, ag, vf = sg.mk, sg.ag, sg.vf
OUT = os.path.join(ag.ROOT, "strumenti", "risultati", "senso")
PROPS = os.path.join(OUT, "proprieta.jsonl")
RUNS = os.path.join(OUT, "esiti.jsonl")
OPTIONS = {"temperature": 0, "seed": 1, "num_ctx": 4096, "num_predict": 900}
PROMPT = """Here is the specification of a Python function:

```python
{spec}
```

Write a Python function `check_properties(candidate)` that tests whether `candidate` (an implementation of this function) is correct. Call `candidate` on at least 8 different inputs that you choose, including edge cases (empty inputs, single elements, zeros, negative numbers, duplicates, large values when relevant), and use `assert` to check properties that any correct implementation must satisfy: exact outputs you are certain about, or relations between inputs and outputs. Do not write the function itself, and do not use any library outside the standard library. Reply with only the code, in one ```python block."""


def pool():
    """The visible-pass solutions with a strict label, as in the secondo sguardo (task 32 excluded)."""
    with open(os.path.join(sg.OUT, "canonical_ok.json"), encoding="utf-8") as fh:
        canon = {int(k): v for k, v in json.load(fh).items()}
    with open(sg.LABELS, encoding="utf-8") as fh:
        labs = [x for x in map(json.loads, fh)]
    return [x for x in labs if canon.get(x["task"]) == 1 and x["visible_pass"] == 1 and x["strict_pass"] in (0, 1)]


def write_props():
    os.makedirs(OUT, exist_ok=True)
    rows = ag.load_rows()
    tasks = sorted({x["task"] for x in pool()})
    done = set()
    if os.path.exists(PROPS):
        with open(PROPS, encoding="utf-8") as fh:
            done = {json.loads(x)["task"] for x in fh}
    with open(PROPS, "a", encoding="utf-8") as out:
        for idx in tasks:
            if idx in done:
                continue
            body = {"model": mk.VOICES["gemma"], "stream": False, "think": False, "options": OPTIONS,
                    "messages": [{"role": "user", "content": PROMPT.format(spec=rows[idx]["prompt"].strip())}]}
            req = urllib.request.Request(ag.OLLAMA, data=json.dumps(body).encode(),
                                         headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                text = (json.load(r).get("message") or {}).get("content") or ""
            m = sg.CODE_BLOCK.search(text)
            code = m.group(1).strip() if m else ""
            try:
                ast.parse(code)                       # syntax check only: nothing is executed on the host
                valid = "def check_properties" in code
            except SyntaxError:
                valid = False
            out.write(json.dumps({"task": idx, "reply": text, "code": code, "valid": valid}, ensure_ascii=False) + "\n")
            out.flush()
    print("properties written for", len(tasks), "tasks")


def solution_text(x, rows):
    if x["part"] == "A":
        return sg.full_solution_A({"pid": x["pid"]})
    return sg.imports_of(rows[x["task"]]["prompt"]) + "\n\n" + x["code"] + "\n"


def run_props():
    rows = ag.load_rows()
    with open(PROPS, encoding="utf-8") as fh:
        props = {p["task"]: p for p in map(json.loads, fh)}
    done = set()
    if os.path.exists(RUNS):
        with open(RUNS, encoding="utf-8") as fh:
            done = {json.loads(x)["pid"] for x in fh}
    with open(RUNS, "a", encoding="utf-8") as out:
        for x in pool():
            if x["pid"] in done:
                continue
            p = props.get(x["task"])
            if not p or not p["valid"]:
                res = None                                # no sense built for this task
            else:
                test = p["code"] + "\n\n\ndef check(candidate):\n    check_properties(candidate)\n"
                res = sg.run_tests(solution_text(x, rows), test, rows[x["task"]]["entry_point"], "PROPS", 30)
            out.write(json.dumps({"pid": x["pid"], "task": x["task"], "part": x["part"], "strict_pass": x["strict_pass"],
                                  "props_pass": res}) + "\n")
            out.flush()
    print("checks run")


def evaluate():
    with open(RUNS, encoding="utf-8") as fh:
        runs = [x for x in map(json.loads, fh)]
    with open(PROPS, encoding="utf-8") as fh:
        props = {p["task"]: p for p in map(json.loads, fh)}
    bad = [r for r in runs if r["strict_pass"] == 0]
    good = [r for r in runs if r["strict_pass"] == 1]

    def flags(rs, flag):
        return sum(1 for r in rs if flag(r))
    raw = lambda r: r["props_pass"] == 0
    # exploratory consensus filter: a task whose checks fail on all of its (2 or more) solutions is not trusted
    by_task = {}
    for r in runs:
        by_task.setdefault(r["task"], []).append(r)
    distrust = {t for t, rs in by_task.items() if len(rs) >= 2 and all(x["props_pass"] == 0 for x in rs)}
    filtered = lambda r: r["props_pass"] == 0 and r["task"] not in distrust
    res = {"solutions": len(runs), "false_done": len(bad), "good": len(good),
           "tasks_with_valid_checks": sum(1 for p in props.values() if p["valid"]), "tasks": len(props),
           "unclear_runs": sum(1 for r in runs if r["props_pass"] is None)}
    for name, fl in (("raw", raw), ("consensus_filter_exploratory", filtered)):
        caught, alarms = flags(bad, fl), flags(good, fl)
        res[name] = {"caught": caught, "catch_rate": round(caught / len(bad), 3), "false_alarms": alarms,
                     "false_alarm_rate": round(alarms / len(good), 3)}
    g = res["raw"]
    res["gate"] = {"catch_ge_half": g["caught"] >= len(bad) / 2, "false_alarms_le_10pct": g["false_alarm_rate"] <= 0.10}
    res["gate"]["passes"] = all(res["gate"].values())
    # the fresh-look judge at the same false-alarm rate
    scores = {}
    for path in (os.path.join(mk.OUT, "risposte_gemma.jsonl"), os.path.join(sg.OUT, "giudizi_gemma.jsonl")):
        with open(path, encoding="utf-8") as fh:
            scores.update({a["pid"]: a["score"] for a in map(json.loads, fh)})
    gs = sorted(scores[r["pid"]] for r in good)
    k = g["false_alarms"]
    thr = gs[k - 1] if k > 0 else float("-inf")
    res["judge_same_false_alarms"] = {"false_alarms": k, "caught": sum(1 for r in bad if scores[r["pid"]] <= thr)}
    res["code_sha256"] = __import__("hashlib").sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    with open(os.path.join(OUT, "senso_risultati.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"scrivi": write_props, "prova": run_props, "valuta": evaluate}[sys.argv[1]]()
