"""Fumo, prove A, B e C (PIANO_AB.md).

A, "il punto di arrivo" (oracle, uses the true patch): did the agent reach a file the fix changes within the first
  K steps? If even this says nothing about the outcome, no early detector can work.
B, "il fumo nel compito": predict each agent's failure from the task text only, before the run starts.
C, "il disaccordo degli esploratori" (descriptive): do the three SWE-bench agents look at the same files early?
  python ab.py estrai   paths touched per step (fumo_percorsi.jsonl)
  python ab.py valuta   A, B and C; writes strumenti/risultati/fumo/ab_risultati.json
"""
import collections
import hashlib
import json
import math
import os
import random
import re
import sys

import numpy as np

import fumo
import valuta_fumo as vf

VERIFIED = os.path.join(fumo.EXT, "swebench-verified", "test-00000-of-00001.parquet")
PATHS = os.path.join(fumo.OUT, "fumo_percorsi.jsonl")
RESULTS = os.path.join(fumo.OUT, "ab_risultati.json")
PY_PATH = re.compile(r"(?:/[\w.+-]+)*/?[\w.+-]+(?:/[\w.+-]+)*\.py\b")
ROOT_PREFIX = re.compile(r"^/(?:workspace|testbed|repo)/(?:[\w.+-]+/)?")
DIFF_FILE = re.compile(r"^diff --git a/(\S+) b/(\S+)", re.M)
EDIT_CMDS = ("create", "str_replace", "insert", "undo_edit")


def rel_paths(text):
    """Repository-relative .py paths in a piece of text (absolute workspace prefixes removed)."""
    out = set()
    for p in PY_PATH.findall(text or ""):
        p = p.strip()
        if p.startswith("/"):
            p = ROOT_PREFIX.sub("", p)
        out.add(p.lstrip("./"))
    return sorted(x for x in out if x)


def touches(paths, gold):
    """True if a mentioned path is a gold file (suffix match in either direction, at least two segments)."""
    for p in paths:
        for g in gold:
            if p == g or g.endswith("/" + p) and p.count("/") >= 1 or p.endswith("/" + g):
                return True
    return False


# ---------- extraction: paths per step ----------

def openhands_paths(agent, trajs, results):
    outcomes = fumo.formati.load_outcomes(os.path.join(fumo.EXT, "swebench-results", results, "results.json"))
    for run in fumo.formati.openhands_events(os.path.join(fumo.EXT, "swebench-trajs", trajs), outcomes):
        steps = []
        for m in run["messages"] or []:
            if m.get("role") == "assistant":
                for c in m.get("tool_calls") or []:
                    args = c["function"].get("arguments") or ""
                    try:
                        a = json.loads(args) if isinstance(args, str) else args
                    except ValueError:
                        a = {}
                    a = a if isinstance(a, dict) else {}
                    edit = c["function"]["name"] == "str_replace_editor" and a.get("command") in EDIT_CMDS
                    text = (a.get("path") or "") + " " + (a.get("command") if isinstance(a.get("command"), str) else "")
                    steps.append({"p": rel_paths(text), "edit": int(edit)})
            elif m.get("role") == "error":
                steps.append({"p": [], "edit": 0})
        yield {"agent": agent, "id": run["id"], "task": run["task"], "outcome": run["outcome"], "steps": steps}


def observation_paths(agent, trajs, results):
    outcomes = fumo.formati.load_outcomes(os.path.join(fumo.EXT, "swebench-results", results, "results.json"))
    for run in fumo.formati.observation_logs(os.path.join(fumo.EXT, "swebench-trajs", trajs), outcomes):
        steps = []
        for tool, text in run["observations"] or []:
            # first line only: the file opened or edited, or the command (a directory listing would name many files)
            head = (text or "").split("\n", 1)[0]
            eo = fumo.formati.editor_outcome(text) if tool in ("file_editor", "str_replace_editor") else None
            edit = eo in ("edited", "created", "undo", "noop", "missing", "multiple")
            steps.append({"p": rel_paths(head), "edit": int(bool(edit))})
        yield {"agent": agent, "id": run["id"], "task": run["task"], "outcome": run["outcome"], "steps": steps}


def gemma_paths(agent, folder, _):
    import ast as _ast
    import glob
    for f in sorted(glob.glob(os.path.join(folder, "*.json"))):
        if ".infra_" in os.path.basename(f):
            continue
        with open(f, encoding="utf-8") as fh:
            r = json.load(fh)
        if not r.get("gold_defs"):
            continue
        steps = []
        for m in r["messages"]:
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
                args = fn.get("arguments") if isinstance(fn.get("arguments"), dict) else {}
                p = [args["filepath"]] if fn.get("name") == "read_file" and isinstance(args.get("filepath"), str) else []
                steps.append({"p": [x.lstrip("./") for x in p], "edit": 0})
        yield {"agent": agent, "id": f"{r['task']}_{r['condition']}", "task": r["task"],
               "outcome": "resolved" if r["hit"]["fn_exact"] else "unresolved", "steps": steps,
               "gold": sorted(set(r.get("gold_files") or []))}


def extract():
    readers = {"openhands": openhands_paths, "observations": observation_paths, "gemma": gemma_paths}
    counts = collections.Counter()
    with open(PATHS, "w", encoding="utf-8") as out:
        for agent, (kind, a, b) in fumo.AGENTS.items():
            for run in readers[kind](agent, a, b):
                out.write(json.dumps(run, ensure_ascii=False) + "\n")
                counts[agent] += 1
    print(dict(counts))


# ---------- data ----------

def verified():
    import pyarrow.parquet as pq
    t = pq.read_table(VERIFIED).to_pylist()
    return {r["instance_id"]: r for r in t}


def gold_files(patch):
    return sorted({m.group(2) for m in DIFF_FILE.finditer(patch or "")})


def load_paths():
    with open(PATHS, encoding="utf-8") as fh:
        return [json.loads(x) for x in fh]


# ---------- A: the oracle ----------

def test_a(share):
    tasks = verified()
    by = collections.defaultdict(list)
    for r in load_paths():
        by[r["agent"]].append(r)
    out = {}
    for agent, rs in sorted(by.items()):
        K = vf.checkpoint([len(r["steps"]) for r in rs], share)
        rows = []
        for r in rs:
            if len(r["steps"]) <= K:
                continue
            gold = r.get("gold") or gold_files((tasks.get(r["task"]) or {}).get("patch"))
            if not gold:
                continue
            w = r["steps"][:K]
            first = next((i + 1 for i, s in enumerate(w) if touches(s["p"], gold)), K + 1)
            rows.append({"fail": int(r["outcome"] != "resolved"), "first": first,
                         "seen": int(first <= K), "edited": int(any(s["edit"] and touches(s["p"], gold) for s in w))})
        y = [x["fail"] for x in rows]
        seen = [x for x in rows if x["seen"]]
        unseen = [x for x in rows if not x["seen"]]
        out[agent] = {"K": K, "runs": len(rows), "fail": sum(y),
                      "auc_first_gold_step": round(vf.auc([x["first"] for x in rows], y), 3),
                      "auc_edited_gold": round(vf.auc([1 - x["edited"] for x in rows], y), 3),
                      "share_seen_gold": round(len(seen) / len(rows), 3),
                      "fail_rate_seen": round(sum(x["fail"] for x in seen) / len(seen), 3) if seen else None,
                      "fail_rate_unseen": round(sum(x["fail"] for x in unseen) / len(unseen), 3) if unseen else None}
    hits = [a for a, v in out.items() if v["auc_first_gold_step"] >= 0.65]
    return {"per_agent": out, "_agents_auc_ge_0.65": len(hits), "_information_exists_early": len(hits) >= 3}


# ---------- B: before the run, from the task text ----------

CODE_BLOCK = re.compile(r"```")
TRACEBACK = re.compile(r"Traceback \(most recent call last\)")
BACKTICK = re.compile(r"`[^`\n]{1,80}`")
URL = re.compile(r"https?://\S+")
WORD = re.compile(r"[A-Za-z_][A-Za-z0-9_]{2,}")
DIFFICULTY = {"<15 min fix": 0, "15 min - 1 hour": 1, "1-4 hours": 2, ">4 hours": 3}


def task_features(t, repos):
    text = (t["problem_statement"] or "") + "\n" + (t["hints_text"] or "")
    f = [math.log1p(len(text)), len(CODE_BLOCK.findall(text)) / 2, float(bool(TRACEBACK.search(text))),
         float(len(rel_paths(text))), float(len(BACKTICK.findall(text))), float("expected" in text.lower()),
         float(len(URL.findall(text))), math.log1p(len(t["hints_text"] or ""))]
    return f + [float(t["repo"] == r) for r in repos]


def hashed_words(t, dims=4096):
    text = ((t["problem_statement"] or "") + " " + (t["hints_text"] or "")).lower()
    v = np.zeros(dims)
    for w in WORD.findall(text):
        v[int(hashlib.md5(w.encode()).hexdigest()[:8], 16) % dims] += 1.0
    return np.log1p(v)


def test_b():
    tasks = verified()
    outcomes = collections.defaultdict(dict)
    for r in fumo.load():
        if r["agent"] != "gemma4_e4b" and r["task"] in tasks:
            outcomes[r["agent"]][r["task"]] = int(r["outcome"] != "resolved")
    agents = sorted(outcomes)
    ids = sorted(set.intersection(*(set(outcomes[a]) for a in agents)))
    repos = sorted({tasks[i]["repo"] for i in ids})
    hand = np.array([task_features(tasks[i], repos) for i in ids])
    hand = (hand - hand.mean(0)) / np.where(hand.std(0) > 0, hand.std(0), 1)
    words = np.array([hashed_words(tasks[i]) for i in ids])
    words = (words - words.mean(0)) / np.where(words.std(0) > 0, words.std(0), 1)
    order = list(range(len(ids)))
    random.Random(fumo.SEED).shuffle(order)
    folds = [set(order[f::5]) for f in range(5)]
    res = {"tasks": len(ids), "agents": agents}
    for name, X, lam in (("B1_hand", hand, 1.0), ("B2_hand_words", np.hstack([hand, words]), 50.0)):
        scores = {a: [0.0] * len(ids) for a in agents}
        for fold in folds:
            tr = [i for i in range(len(ids)) if i not in fold]
            Xtr = np.vstack([np.hstack([X[tr], np.tile(np.eye(len(agents))[k], (len(tr), 1))]) for k in range(len(agents))])
            ytr = np.concatenate([[outcomes[a][ids[i]] for i in tr] for a in agents]).astype(float)
            w = vf.fit_logit(Xtr, ytr, lam=lam)
            for k, a in enumerate(agents):
                for i in fold:
                    x = np.concatenate([[1.0], X[i], np.eye(len(agents))[k]])
                    scores[a][i] = float(x @ w)
        per = {}
        for a in agents:
            y = [outcomes[a][i] for i in ids]
            s = scores[a]
            succ = sorted(v for v, t in zip(s, y) if t == 0)
            thr = succ[int(0.98 * len(succ))] if succ else None
            per[a] = {"auc": round(vf.auc(s, y), 3),
                      "skip_fail_at_2pct": round(sum(v > thr and t for v, t in zip(s, y)) / max(1, sum(y)), 3)}
        res[name] = {"per_agent": per, "_mean_auc": round(sum(v["auc"] for v in per.values()) / len(per), 3)}
        res[name]["_promising"] = res[name]["_mean_auc"] >= 0.70
    diff = {a: round(vf.auc([DIFFICULTY.get(tasks[i]["difficulty"], 1) for i in ids], [outcomes[a][i] for i in ids]), 3)
            for a in agents}
    res["reference_human_difficulty_auc"] = diff
    return res


# ---------- C: do the explorers agree early? ----------

def test_c(share):
    by = collections.defaultdict(dict)
    lengths = collections.defaultdict(list)
    for r in load_paths():
        if r["agent"] != "gemma4_e4b":
            by[r["agent"]][r["task"]] = r
            lengths[r["agent"]].append(len(r["steps"]))
    ks = {a: vf.checkpoint(lengths[a], share) for a in by}
    agents = sorted(by)
    common = sorted(set.intersection(*(set(by[a]) for a in agents)))

    def early(a, t):
        return {p for s in by[a][t]["steps"][:ks[a]] for p in s["p"]}
    out = {}
    for a in agents:
        scores, y = [], []
        for t in common:
            mine = early(a, t)
            others = [early(b, t) for b in agents if b != a]
            jac = [len(mine & o) / len(mine | o) if (mine | o) else 0.0 for o in others]
            scores.append(-sum(jac) / len(jac))           # low agreement -> higher failure score
            y.append(int(by[a][t]["outcome"] != "resolved"))
        out[a] = {"auc_low_agreement": round(vf.auc(scores, y), 3), "tasks": len(common)}
    return {"checkpoint": ks, "per_agent": out}


def run():
    res = {"A_main": test_a(0.3), "A_half": test_a(0.5), "B": test_b(), "C_descriptive": test_c(0.3),
           "code_sha256": {f: hashlib.sha256(open(os.path.join(fumo.HERE, f), "rb").read()).hexdigest()
                           for f in ("fumo.py", "valuta_fumo.py", "ab.py")},
           "verified_sha256": hashlib.sha256(open(VERIFIED, "rb").read()).hexdigest()}
    with open(RESULTS, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"estrai": extract, "valuta": run}[sys.argv[1]]()
