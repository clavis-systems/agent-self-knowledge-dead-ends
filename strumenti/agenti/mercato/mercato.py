"""Mercato dei pensieri, quick gate (PIANO_MERCATO.md): do small "voices" betting yes/no on a finished fix predict
the hidden tests, and does their market add anything to simply running the visible tests?
  python mercato.py costruisci     CPU + WASM sandbox: unique (task, final file) pairs, spec, code, visible-test result
  python mercato.py chiedi MODEL   GPU: one stateless yes/no question per pair (answers cached)
  python mercato.py valuta         AUCs, cross-validated market, gate decision
"""
import ast
import glob
import hashlib
import json
import math
import os
import random
import sys
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "modifiche")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "fumo")))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "valutazione")))
import agente_gemma as ag  # noqa: E402
import valuta_fumo as vf  # noqa: E402  (auc, fit_logit)

ROOT = ag.ROOT
RES = os.path.join(ROOT, "strumenti", "risultati")
OUT = os.path.join(RES, "mercato")
PAIRS = os.path.join(OUT, "coppie.jsonl")
SEED = "mercato-2026-10-15"
VOICES = {"gemma": "gemma4:e4b-it-qat", "qwen": "qwen3:8b"}
OPTIONS = {"temperature": 0, "seed": 1, "num_ctx": 8192, "num_predict": 4}
QUESTION = """Here is the specification of a Python function (signature and docstring) and an implementation.

Specification:
```python
{spec}
```

Implementation:
```python
{code}
```

Does the implementation do exactly what the docstring says, for all inputs? Answer yes or no."""


def runs():
    """(task index, final file, solved) of every finished run we have, October and today."""
    for f in glob.glob(os.path.join(RES, "prova_gemma", "prova", "*.json")):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        yield int(os.path.basename(f)[:3]), r["final_file"], r["solved"]
    for f in glob.glob(os.path.join(RES, "sogno", "1a", "*.json")):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        for k in ("with_lesson", "without"):
            yield r["task"], r[k]["final_file"], r[k]["solved"]
    for f in glob.glob(os.path.join(RES, "sogno", "giorno2", "*.json")):
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        yield int(os.path.basename(f).rsplit("_", 1)[1][:3]), r["final_file"], r["solved"]   # "task" holds "Python/N"


def function_code(text, name):
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return text[:4000], False
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return ast.get_source_segment(text, node) or text[:4000], True
    return text[:4000], False


def build():
    os.makedirs(OUT, exist_ok=True)
    rows = ag.load_rows()
    seen, pairs, conflicts = {}, [], 0
    for idx, final, solved in runs():
        if solved is None:
            continue
        key = (idx, hashlib.sha256(final.encode()).hexdigest())
        if key in seen:
            conflicts += seen[key] != solved
            continue
        seen[key] = solved
        row = rows[idx]
        code, parsed = function_code(final, row["entry_point"])
        program = ag.test_program(row["example_test"], row["entry_point"], "TESTS", row.get("test_setup") or "")
        ok, out = ag.sandbox_run(program, {ag.FILE: final})
        pairs.append({"pid": f"{idx}_{key[1][:10]}", "task": idx, "solved": int(bool(solved)), "spec": row["prompt"],
                      "code": code, "parsed": parsed, "visible_pass": int(bool(ok))})
    with open(PAIRS, "w", encoding="utf-8") as fh:
        for p in pairs:
            fh.write(json.dumps(p, ensure_ascii=False) + "\n")
    print({"pairs": len(pairs), "solved": sum(p["solved"] for p in pairs), "tasks": len({p["task"] for p in pairs}),
           "label_conflicts_between_identical_files": conflicts, "unparsed": sum(not p["parsed"] for p in pairs)})


def load_pairs():
    with open(PAIRS, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh]


def score(first):
    tops = (first or {}).get("top_logprobs") or []
    y = sum(math.exp(t["logprob"]) for t in tops if t["token"].strip().lower() == "yes")
    n = sum(math.exp(t["logprob"]) for t in tops if t["token"].strip().lower() == "no")
    return y - n


def ask(model, text):
    body = {"model": model, "messages": [{"role": "user", "content": text}], "stream": False, "think": False,
            "options": OPTIONS, "logprobs": True, "top_logprobs": 20}
    req = urllib.request.Request(ag.OLLAMA, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)


def chiedi(voice):
    model = VOICES[voice]
    path = os.path.join(OUT, f"risposte_{voice}.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            done = {json.loads(x)["pid"] for x in fh if x.strip()}
    with open(path, "a", encoding="utf-8") as out:
        for p in load_pairs():
            if p["pid"] in done:
                continue
            r = ask(model, QUESTION.format(spec=p["spec"].strip(), code=p["code"]))
            first = (r.get("logprobs") or [None])[0]
            out.write(json.dumps({"pid": p["pid"], "model": model, "reply": (r.get("message") or {}).get("content"),
                                  "score": score(first), "first_token": first}, ensure_ascii=False) + "\n")
            out.flush()
    print(voice, "done")


def cv_scores(X, y, groups, folds=5):
    keys = sorted(set(groups))
    random.Random(SEED).shuffle(keys)
    fold_of = {k: i % folds for i, k in enumerate(keys)}
    s = np.zeros(len(y))
    for f in range(folds):
        tr = [i for i, g in enumerate(groups) if fold_of[g] != f]
        te = [i for i, g in enumerate(groups) if fold_of[g] == f]
        w = vf.fit_logit(X[tr], y[tr])
        s[te] = np.hstack([np.ones((len(te), 1)), X[te]]) @ w
    return s


def valuta():
    pairs = load_pairs()
    ans = {}
    for voice in VOICES:
        with open(os.path.join(OUT, f"risposte_{voice}.jsonl"), encoding="utf-8") as fh:
            ans[voice] = {a["pid"]: a["score"] for a in map(json.loads, fh)}
    pairs = [p for p in pairs if all(p["pid"] in ans[v] for v in VOICES)]
    y = np.array([p["solved"] for p in pairs], dtype=float)
    groups = [p["task"] for p in pairs]
    V = np.array([[ans[v][p["pid"]] for v in VOICES] for p in pairs])
    Z = (V - V.mean(0)) / np.where(V.std(0) > 0, V.std(0), 1)
    vis = np.array([[p["visible_pass"]] for p in pairs], dtype=float)
    a = lambda s: round(vf.auc(list(s), list(y)), 3)
    res = {"pairs": len(pairs), "solved": int(y.sum()), "tasks": len(set(groups)),
           "auc": {f"voice_{v}": a(V[:, i]) for i, v in enumerate(VOICES)}}
    res["auc"]["market_simple"] = a(Z.mean(1))
    res["auc"]["market_memory_cv"] = a(cv_scores(Z, y, groups))
    res["auc"]["visible_tests"] = a(vis[:, 0])
    res["auc"]["visible_plus_market_cv"] = a(cv_scores(np.hstack([vis, Z]), y, groups))
    best_voice = max(res["auc"][f"voice_{v}"] for v in VOICES)
    res["gate"] = {"1_market_beats_best_voice_by_0.03": res["auc"]["market_memory_cv"] >= best_voice + 0.03,
                   "2_market_adds_0.03_to_visible_tests": res["auc"]["visible_plus_market_cv"] >= res["auc"]["visible_tests"] + 0.03}
    res["gate"]["passes"] = all(res["gate"].values())
    vp = [p for p in pairs if p["visible_pass"]]
    res["among_visible_pass"] = {"pairs": len(vp), "solved": sum(p["solved"] for p in vp),
                                 **{f"auc_{v}": round(vf.auc([ans[v][p["pid"]] for p in vp], [p["solved"] for p in vp]) or 0, 3)
                                    for v in VOICES}}
    res["code_sha256"] = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    with open(os.path.join(OUT, "mercato_risultati.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"costruisci": build, "chiedi": lambda: chiedi(sys.argv[2]), "valuta": valuta}[sys.argv[1]]()
