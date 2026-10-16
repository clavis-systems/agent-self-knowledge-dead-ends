"""Istinto e sogno (PIANO_ISTINTO_SOGNO.md): quick gates on HumanEvalFix with the October Gemma agent.

The agent, its tools, the sandbox and the hidden-test check are those of strumenti/agenti/modifiche/agente_gemma.py,
imported unchanged. This file adds only: the statement extra (lessons), the emotions and their reactions, the dream.
  python istinto_sogno.py cancello0          CPU: emotions on the October "off" runs (no model)
  python istinto_sogno.py sogno              GPU: gate 1a, dreams on D1 and retries with and without the lesson
  python istinto_sogno.py giorno2 COND       GPU: BASE | SOGNO | ISTINTO | ISTINTO_SOGNO on D2 + S2
  python istinto_sogno.py riassumi           gate decisions from the saved results
"""
import glob
import hashlib
import json
import os
import random
import secrets
import sys
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "modifiche")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "valutazione")))
import agente_gemma as ag  # noqa: E402

ROOT = ag.ROOT
OCT = os.path.join(ROOT, "strumenti", "risultati", "prova_gemma", "prova")
OUT = os.path.join(ROOT, "strumenti", "risultati", "sogno")
SEED = "istinto-sogno-2026-10-15"
EXPECTED = {"model_digest": "ee6656371218", "ollama_version": "0.32.13"}
CALLS_LEFT = 5
REACTIONS = {
    "disagio": "[Host] The tests failed twice in a row after your edit. Stop and re-read the docstring and the failing "
               "line. Write in one sentence what the function must do differently, then fix it.",
    "noia": "[Host] You are repeating yourself. Try a different approach: view the function again and change your plan.",
    "fatica": "[Host] You have used 12 of 20 calls. Focus the remaining calls on the single most likely fix, then run "
              "the tests.",
}
PLACEBO_TIPS = [   # written on 15/10 after gate 1a and BEFORE any day-2 run; not derived from any failure
    "When fixing a bug, re-read the docstring before you edit.",
    "When the tests fail, read the failing line and compare the expected and actual values.",
    "When a loop is involved, check its start and end values.",
    "When a condition is involved, check whether < or <= is intended.",
    "When strings are involved, check spaces and letter case.",
    "When numbers are involved, check integer versus float division.",
    "When a list is returned, check its order and duplicates.",
    "When you think you are done, run the tests once more before calling finish.",
]
DREAM = """Earlier today you tried to fix a bug in the function `{entry}` of solution.py and you FAILED: the hidden tests did not pass.

Your final version of solution.py:
```python
{final}
```

The end of the hidden test output:
```
{out}
```

Think about why your fix was wrong. Then write ONE lesson for your future self, to fix bugs in OTHER functions too.
Rules: at most 2 sentences; start with "When"; do not mention `{entry}` or its specific values. Write only the lesson."""


# ---------- the October runs ----------

def october():
    runs = {}
    for f in sorted(glob.glob(os.path.join(OCT, "*_off.json"))):
        with open(f, encoding="utf-8") as fh:
            runs[int(os.path.basename(f)[:3])] = json.load(fh)
    return runs


def split(runs=None):
    runs = runs or october()
    failed = sorted(i for i, r in runs.items() if r["solved"] is False)
    solved = sorted(i for i, r in runs.items() if r["solved"] is True)
    rng = random.Random(SEED)
    rng.shuffle(failed)
    rng.shuffle(solved)
    return {"D1": sorted(failed[:13]), "D2": sorted(failed[13:]), "S2": sorted(solved[:14])}


# ---------- emotions ----------

class Emotions:
    """Fires each emotion at most once; update() returns the emotions that fire at call n (1-based)."""

    def __init__(self):
        self.seen, self.edited, self.fails_in_row, self.texts_in_row, self.fired = set(), False, 0, 0, {}

    def update(self, n, kind, key, result):
        new = []
        if kind == "edit" and "has been edited" in (result or ""):
            self.edited = True
        if kind == "test":
            failed = "exit code 1" in (result or "")
            self.fails_in_row = self.fails_in_row + 1 if failed else 0
            if failed and self.edited and self.fails_in_row >= 2:
                new.append("disagio")
        repeat = key is not None and key in self.seen
        if key is not None:
            self.seen.add(key)
        self.texts_in_row = self.texts_in_row + 1 if kind == "text" else 0
        if repeat or self.texts_in_row >= 2:
            new.append("noia")
        if n >= 12 and kind != "finish":
            new.append("fatica")
        new = [e for e in new if e not in self.fired]
        for e in new:
            self.fired[e] = n
        return new


def kind_of(name, args):
    if name in ("view", "str_replace"):
        return "view" if name == "view" else "edit"
    if name in ("str_replace_editor",):
        return "view" if args.get("command") == "view" else "edit"
    if name in ("run_tests", "execute_bash"):
        return "test"
    return "finish" if name == "finish" else "other"


def replay_emotions(messages):
    """Emotions over an October log (tool calls recorded with the OpenHands-style names)."""
    em, n = Emotions(), 0
    msgs = messages[2:]
    for k, m in enumerate(msgs):
        if m.get("role") != "assistant":
            continue
        n += 1
        if m.get("tool_calls"):
            fn = m["tool_calls"][0]["function"]
            args = json.loads(fn["arguments"]) if isinstance(fn["arguments"], str) else fn["arguments"]
            res = msgs[k + 1]["content"] if k + 1 < len(msgs) and msgs[k + 1].get("role") == "tool" else ""
            em.update(n, kind_of(fn["name"], args), json.dumps([fn["name"], args], sort_keys=True), res)
        else:
            em.update(n, "text", None, "")
    return em.fired


def gate0():
    runs = october()
    rows = [(r["solved"], replay_emotions(r["messages"])) for r in runs.values() if r["solved"] is not None]
    overall = sum(not s for s, _ in rows) / len(rows)
    out = {"runs": len(rows), "overall_fail_rate": round(overall, 3), "emotions": {}}
    for e in REACTIONS:
        fired = [(s, f) for s, f in rows if e in f and f[e] <= ag.MAX_CALLS - CALLS_LEFT]
        share = len(fired) / len(rows)
        fail = sum(not s for s, _ in fired) / len(fired) if fired else None
        out["emotions"][e] = {"fired_with_5_left": len(fired), "share": round(share, 3),
                              "fail_rate_when_fired": round(fail, 3) if fail is not None else None,
                              "passes": share >= 0.10 and fail is not None and fail >= 0.50}
    out["passing"] = [e for e, v in out["emotions"].items() if v["passes"]]
    return out


# ---------- live runs ----------

def chat_plain(prompt, num_predict=200):
    body = {"model": ag.MODEL, "messages": [{"role": "user", "content": prompt}], "stream": False, "think": False,
            "options": dict(ag.OPTIONS, num_predict=num_predict)}
    req = urllib.request.Request(ag.OLLAMA, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return (json.load(r).get("message") or {}).get("content") or ""


def run_x(task, extra="", reactions=(), chat=ag.ollama_chat, runner=ag.sandbox_run, max_calls=ag.MAX_CALLS):
    """agente_gemma.run_task with two additions: `extra` after the statement, and host reactions appended to the
    result of the call at which an emotion in `reactions` fires. Everything else is the October loop."""
    ws = ag.Workspace(task, "off", runner)
    sent = [{"role": "system", "content": ag.SYSTEM}, {"role": "user", "content": task["statement"] + extra}]
    log = [dict(m) for m in sent]
    em, calls, finished, started = Emotions(), 0, False, time.time()
    hidden, out, infra, notes = None, "", None, []
    try:
        while calls < max_calls and not finished:
            reply = chat(sent)
            msg = reply.get("message") or {}
            tool_calls = msg.get("tool_calls") or []
            if not tool_calls:
                calls += 1
                nudge = "Use the tools. Call finish when the tests pass."
                for e in em.update(calls, "text", None, ""):
                    if e in reactions:
                        nudge += "\n" + REACTIONS[e]
                        notes.append([calls, e])
                sent += [{"role": "assistant", "content": msg.get("content") or ""}, {"role": "user", "content": nudge}]
                log += [{"role": "assistant", "content": msg.get("content") or ""}, {"role": "user", "content": nudge}]
                continue
            sent.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": tool_calls})
            for tc in tool_calls:
                if calls >= max_calls:
                    break
                fn = tc.get("function") or {}
                name, args = fn.get("name"), fn.get("arguments") or {}
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {}
                result = ws.call(name, args)
                calls += 1
                for e in em.update(calls, kind_of(name, args), json.dumps([name, args], sort_keys=True), result):
                    if e in reactions:
                        result += "\n" + REACTIONS[e]
                        notes.append([calls, e])
                sent.append({"role": "tool", "content": result})
                log += [{"role": "assistant", "content": msg.get("content") or "", "tool_calls": [{"function": {"name": name, "arguments": args}}]},
                        {"role": "tool", "content": result}]
                if name == "finish":
                    finished = True
                    break
        nonce = secrets.token_hex(8)
        program = ag.test_program(task["hidden_test"], task["entry_point"], "HIDDEN TESTS", task.get("test_setup", ""),
                                  nonce, hide=True)
        ok, out = runner(program, dict(ws.files))
        if out.lstrip().startswith(ag.NOT_REMOVED):
            raise ag.InfraError(f"sandbox: the test file could not be removed: {out.strip()[:200]}")
        hidden = ag.hidden_outcome(ok, out, nonce)
    except ag.InfraError as exc:
        infra = str(exc)
    return {"task": task["id"], "solved": hidden == "passed" if hidden in ("passed", "failed") else None,
            "hidden": hidden, "infra_error": infra, "finished": finished, "calls": calls,
            "seconds": round(time.time() - started, 1), "emotions": em.fired, "reaction_notes": notes,
            "hidden_test_output": out[-400:], "final_file": ws.files[ag.FILE], "messages": log}


def config():
    c = ag.run_config(1)
    if not (c["model_digest"] or "").startswith(EXPECTED["model_digest"]) or c["ollama_version"] != EXPECTED["ollama_version"]:
        raise SystemExit(f"model or Ollama differ from the plan: {c['model_digest']} {c['ollama_version']}")
    c["istinto_sogno_sha256"] = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    return c


def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + ".part", "w", encoding="utf-8") as fh:
        json.dump(obj, fh, ensure_ascii=False, indent=1)
    os.replace(path + ".part", path)


def done(path, cfg):
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as fh:
        old = json.load(fh)
    if old.get("config") != cfg:
        raise SystemExit(f"{path}: written by another configuration")
    return old


def dreams():
    cfg, runs, rows = config(), october(), ag.load_rows()
    for idx in split(runs)["D1"]:
        path = os.path.join(OUT, "1a", f"{idx:03d}.json")
        if done(path, cfg):
            continue
        r = runs[idx]
        task = ag.build_task(rows, idx)
        lesson = chat_plain(DREAM.format(entry=task["entry_point"], final=r["final_file"][:6000],
                                         out=(r.get("hidden_test_output") or "")[-400:])).strip()[:400]
        with_lesson = run_x(task, "\n\nA lesson you learned from a past mistake: " + lesson)
        without = run_x(task)
        save(path, {"config": cfg, "task": idx, "lesson": lesson, "with_lesson": with_lesson, "without": without})
        print(idx, "lesson solved", with_lesson["solved"], "| without", without["solved"], "|", lesson[:100], flush=True)


def lessons():
    out = []
    for f in sorted(glob.glob(os.path.join(OUT, "1a", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        if r["with_lesson"]["solved"]:
            out.append(r["lesson"])
    return out


def day2(cond):
    if cond not in ("BASE", "SOGNO", "ISTINTO", "ISTINTO_SOGNO", "PLACEBO"):
        raise SystemExit("condition: BASE | SOGNO | ISTINTO | ISTINTO_SOGNO | PLACEBO")
    cfg, rows, parts = config(), ag.load_rows(), split()
    extra = ""
    if cond == "PLACEBO":       # exploratory control added after gate 1a (Scostamenti): generic advice, no dream
        extra = "\n\nLessons you learned from past mistakes:\n" + "\n".join(f"- {x}" for x in PLACEBO_TIPS)
    if "SOGNO" in cond:
        kept = lessons()
        if not kept:
            raise SystemExit("no verified lesson: gate 1a closed")
        extra = "\n\nLessons you learned from past mistakes:\n" + "\n".join(f"- {x}" for x in kept)
    reactions = tuple(gate0()["passing"]) if "ISTINTO" in cond else ()
    cfg = dict(cfg, condition=cond, extra=extra, reactions=list(reactions))
    for idx in parts["D2"] + parts["S2"]:
        path = os.path.join(OUT, "giorno2", f"{cond}_{idx:03d}.json")
        if done(path, cfg):
            continue
        res = run_x(ag.build_task(rows, idx), extra, reactions)
        save(path, {"config": cfg, "task": idx, "group": "D2" if idx in parts["D2"] else "S2", **res})
        print(cond, idx, "solved", res["solved"], "notes", res["reaction_notes"], flush=True)


def summarize():
    res = {"gate0": gate0(), "split": split()}
    a = []
    for f in sorted(glob.glob(os.path.join(OUT, "1a", "*.json"))):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        a.append((r["task"], bool(r["with_lesson"]["solved"]), bool(r["without"]["solved"]), r["lesson"]))
    if a:
        w, wo = sum(x[1] for x in a), sum(x[2] for x in a)
        res["gate1a"] = {"tasks": len(a), "solved_with_lesson": w, "solved_without": wo, "passes": w - wo >= 4,
                         "lessons": [{"task": t, "kept": k, "lesson": l} for t, k, _, l in a]}
    g2 = {}
    for f in glob.glob(os.path.join(OUT, "giorno2", "*.json")):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        g2.setdefault(r["config"]["condition"], {})[r["task"]] = (r["group"], bool(r["solved"]))
    if g2:
        res["giorno2"] = {c: {"D2_solved": sum(s for g, s in v.values() if g == "D2"),
                              "S2_solved": sum(s for g, s in v.values() if g == "S2"), "runs": len(v)}
                          for c, v in g2.items()}
        base = res["giorno2"].get("BASE")
        for c, v in res["giorno2"].items():
            if c != "BASE" and base:
                need = 6 if c == "ISTINTO_SOGNO" else 4
                v["passes"] = v["D2_solved"] - base["D2_solved"] >= need and base["S2_solved"] - v["S2_solved"] <= 2
    save(os.path.join(OUT, "riassunto.json"), res)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "cancello0":
        print(json.dumps(gate0(), indent=1))
    elif cmd == "sogno":
        dreams()
    elif cmd == "giorno2":
        day2(sys.argv[2])
    elif cmd == "riassumi":
        summarize()
