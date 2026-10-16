"""Secondo sguardo a mente fresca (PIANO_SGUARDO.md): does a fresh yes/no look by a small model catch the false
"done" (visible tests pass, strict HumanEval+ tests fail)?
  python sguardo.py genera          GPU: Gemma writes each HumanEval function from scratch, 3 samples (generati.jsonl)
  python sguardo.py prova           CPU + WASM sandbox: visible and strict tests for A (mercato pairs) and B (generated)
  python sguardo.py giudica VOICE   GPU: fresh yes/no look on the B solutions (A was judged in the mercato)
  python sguardo.py valuta          gate decision
"""
import hashlib
import json
import math
import os
import re
import secrets
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "mercato")))
import mercato as mk  # noqa: E402  (also brings agente_gemma, the WASM sandbox and the AUC)

ag, vf = mk.ag, mk.vf
ROOT = ag.ROOT
PLUS = os.path.join(ROOT, "esterni", "humanevalplus", "test-00000-of-00001-5973903632b82d40.parquet")
OUT = os.path.join(ROOT, "strumenti", "risultati", "sguardo")
GEN = os.path.join(OUT, "generati.jsonl")
LABELS = os.path.join(OUT, "etichette.jsonl")
SEEDS = (1, 2, 3)
GEN_OPTIONS = {"temperature": 0.7, "num_ctx": 4096, "num_predict": 700}
GEN_PROMPT = ("Complete this Python function. Reply with the whole function (signature included) in one ```python "
              "block and nothing else.\n\n```python\n{prompt}\n```")
CODE_BLOCK = re.compile(r"```(?:python)?\s*\n(.*?)```", re.S)
PLUS_PRELUDE = '''
def _close(a, b, rtol, atol):
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return len(a) == len(b) and all(_close(x, y, rtol, atol) for x, y in zip(a, b))
    try:
        return abs(a - b) <= atol + rtol * abs(b)
    except TypeError:
        return a == b


def is_floats(x) -> bool:
    if isinstance(x, float):
        return True
    if isinstance(x, (list, tuple)):
        return all(isinstance(i, float) for i in x)
    return False


def assertion(out, exp, atol):
    exact_match = out == exp
    if atol == 0 and is_floats(exp):
        atol = 1e-6
    if not exact_match and atol != 0:
        assert _close(out, exp, 1e-07, atol)
    else:
        assert exact_match
'''


def plus_rows():
    import pyarrow.parquet as pq
    return pq.read_table(PLUS).to_pylist()


def strict_test(row):
    """HumanEval+ test with the numpy import removed and is_floats/assertion redefined by PLUS_PRELUDE (same
    tolerance rule). Every other helper of the original test (ref_func, _poly, imports) is kept."""
    head, body = row["test"].split("def check(candidate):", 1)
    return head.replace("import numpy as np", "") + PLUS_PRELUDE + "\n\ndef check(candidate):" + body


def imports_of(prompt):
    return "\n".join(x for x in prompt.splitlines() if x.startswith(("import ", "from ")))


def outcome(ok, out, label, nonce):
    if ok and f"{label} PASSED {nonce}" in out:
        return 1
    if "Traceback (most recent call last)" in out or out.startswith(("Timeout:", "Output troppo grande")):
        return 0
    return None


def run_tests(solution_text, test_code, entry, label, timeout):
    nonce = secrets.token_hex(6)
    program = ag.test_program(test_code, entry, label, "", nonce, hide=True)
    ok, out = ag.sandbox_run(program, {ag.FILE: solution_text}, timeout=timeout)
    return outcome(ok, out, label, nonce)


# ---------- B: new solutions ----------

def generate():
    os.makedirs(OUT, exist_ok=True)
    rows = ag.load_rows()
    done = set()
    if os.path.exists(GEN):
        with open(GEN, encoding="utf-8") as fh:
            done = {(g["task"], g["seed"]) for g in map(json.loads, fh)}
    with open(GEN, "a", encoding="utf-8") as out:
        for idx, row in enumerate(rows):
            for seed in SEEDS:
                if (idx, seed) in done:
                    continue
                body = {"model": mk.VOICES["gemma"], "stream": False, "think": False,
                        "messages": [{"role": "user", "content": GEN_PROMPT.format(prompt=row["prompt"].strip())}],
                        "options": dict(GEN_OPTIONS, seed=seed)}
                req = urllib.request.Request(ag.OLLAMA, data=json.dumps(body).encode(),
                                             headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(req, timeout=600) as r:
                    text = (json.load(r).get("message") or {}).get("content") or ""
                m = CODE_BLOCK.search(text)
                code = m.group(1).strip() if m else ""
                out.write(json.dumps({"task": idx, "seed": seed, "reply": text,
                                      "code": code if f"def {row['entry_point']}" in code else ""}, ensure_ascii=False) + "\n")
                out.flush()
        print("generated")


# ---------- tests for A and B ----------

def label_all():
    rows, plus = ag.load_rows(), plus_rows()
    assert all(rows[i]["entry_point"] == plus[i]["entry_point"] for i in range(len(rows))), "dataset order differs"
    todo = []
    for p in mk.load_pairs():                      # A: HumanEvalFix fixes (whole solution.py of the run)
        src = os.path.join(mk.RES, "prova_gemma", "prova")
        todo.append(("A", p["pid"], p["task"], None, p["visible_pass"], p["code"], p))
    seen = set()
    with open(GEN, encoding="utf-8") as fh:
        for g in map(json.loads, fh):
            if not g["code"]:
                continue
            key = (g["task"], hashlib.sha256(g["code"].encode()).hexdigest())
            if key in seen:
                continue
            seen.add(key)
            todo.append(("B", f"B{g['task']}_{key[1][:10]}", g["task"], g["seed"], None, g["code"], None))
    done = set()
    if os.path.exists(LABELS):
        with open(LABELS, encoding="utf-8") as fh:
            done = {json.loads(x)["pid"] for x in fh}
    with open(LABELS, "a", encoding="utf-8") as out:
        for part, pid, idx, seed, visible, code, pair in todo:
            if pid in done:
                continue
            row = rows[idx]
            if part == "A":
                text = full_solution_A(pair)
            else:
                text = imports_of(row["prompt"]) + "\n\n" + code + "\n"
            if visible is None:
                visible = run_tests(text, row["example_test"], row["entry_point"], "TESTS", 30)
            strict = run_tests(text, strict_test(plus[idx]), row["entry_point"], "PLUS", 120)
            out.write(json.dumps({"pid": pid, "part": part, "task": idx, "seed": seed, "visible_pass": visible,
                                  "strict_pass": strict, "code": code}, ensure_ascii=False) + "\n")
            out.flush()
    print("labelled")


_A_FILES = {}


def full_solution_A(pair):
    """The whole final solution.py of the run that produced this mercato pair (found again by hash)."""
    if not _A_FILES:
        for idx, final, _solved in mk.runs():
            _A_FILES[f"{idx}_{hashlib.sha256(final.encode()).hexdigest()[:10]}"] = final
    return _A_FILES[pair["pid"]]


def canonical():
    """Tasks whose official HumanEval+ solution passes the strict test here; the others are excluded."""
    rows, plus = ag.load_rows(), plus_rows()
    ok = {i: run_tests(p["prompt"] + p["canonical_solution"], strict_test(p), rows[i]["entry_point"], "PLUS", 120)
          for i, p in enumerate(plus)}
    with open(os.path.join(OUT, "canonical_ok.json"), "w", encoding="utf-8") as fh:
        json.dump(ok, fh)
    print("canonical failing:", [i for i, v in ok.items() if v != 1])


# ---------- the fresh look on B ----------

def judge(voice):
    rows = ag.load_rows()
    path = os.path.join(OUT, f"giudizi_{voice}.jsonl")
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            done = {json.loads(x)["pid"] for x in fh}
    with open(LABELS, encoding="utf-8") as fh:
        labs = [x for x in map(json.loads, fh) if x["part"] == "B"]
    with open(path, "a", encoding="utf-8") as out:
        for x in labs:
            if x["pid"] in done:
                continue
            r = mk.ask(mk.VOICES[voice], mk.QUESTION.format(spec=rows[x["task"]]["prompt"].strip(), code=x["code"]))
            first = (r.get("logprobs") or [None])[0]
            out.write(json.dumps({"pid": x["pid"], "score": mk.score(first),
                                  "reply": (r.get("message") or {}).get("content")}, ensure_ascii=False) + "\n")
            out.flush()
    print(voice, "judged")


# ---------- the gate ----------

def evaluate():
    with open(os.path.join(OUT, "canonical_ok.json"), encoding="utf-8") as fh:
        canon = {int(k): v for k, v in json.load(fh).items()}
    with open(LABELS, encoding="utf-8") as fh:
        labs = [x for x in map(json.loads, fh) if canon.get(x["task"]) == 1]
    scores = {}
    for voice in mk.VOICES:
        s = {}
        for path in (os.path.join(mk.OUT, f"risposte_{voice}.jsonl"), os.path.join(OUT, f"giudizi_{voice}.jsonl")):
            if os.path.exists(path):
                with open(path, encoding="utf-8") as fh:
                    s.update({a["pid"]: a["score"] for a in map(json.loads, fh)})
        scores[voice] = s
    pool = [x for x in labs if x["visible_pass"] == 1 and x["strict_pass"] in (0, 1)
            and all(x["pid"] in scores[v] for v in mk.VOICES)]
    y = [x["strict_pass"] for x in pool]
    false_done = len(y) - sum(y)
    res = {"labelled": len(labs), "unclear_strict": sum(x["strict_pass"] is None for x in labs),
           "visible_pass_pool": len(pool), "false_done": false_done,
           "parts": {p: {"pool": sum(x["part"] == p for x in pool),
                         "false_done": sum(x["part"] == p and not x["strict_pass"] for x in pool)} for p in ("A", "B")}}
    auc = lambda s, yy: round(vf.auc(s, yy), 3) if 0 < sum(yy) < len(yy) else None
    res["auc"] = {f"judge_{v}": auc([scores[v][x["pid"]] for x in pool], y) for v in mk.VOICES}
    res["auc"]["control_code_length"] = auc([-math.log1p(len(x["code"])) for x in pool], y)
    res["auc_by_part"] = {p: {f"judge_{v}": auc([scores[v][x["pid"]] for x in pool if x["part"] == p],
                                                 [x["strict_pass"] for x in pool if x["part"] == p]) for v in mk.VOICES}
                          for p in ("A", "B")}
    g = res["auc"]["judge_gemma"]
    c = res["auc"]["control_code_length"]
    res["gate"] = {"enough_false_done": false_done >= 40,
                   "gemma_auc_ge_0.75": g is not None and g >= 0.75,
                   "beats_length_by_0.10": g is not None and c is not None and g >= max(c, 1 - c) + 0.10}
    res["gate"]["passes"] = all(res["gate"].values())
    s = sorted(([scores["gemma"][x["pid"]], x["strict_pass"]] for x in pool), key=lambda t: t[0])
    bad = [t for t in s if t[1] == 0]
    if bad:
        cut = bad[len(bad) // 2 - 1][0] if len(bad) >= 2 else bad[0][0]
        flagged_good = sum(1 for sc, ok in s if ok == 1 and sc <= cut)
        res["at_half_false_done_caught"] = {"threshold": round(cut, 4), "good_flagged": flagged_good,
                                            "good_total": sum(y), "share_good_flagged": round(flagged_good / max(1, sum(y)), 3)}
    res["code_sha256"] = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    with open(os.path.join(OUT, "sguardo_risultati.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"genera": generate, "prova": label_all, "canonico": canonical, "giudica": lambda: judge(sys.argv[2]), "valuta": evaluate}[sys.argv[1]]()
