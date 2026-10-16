"""Fumo, evaluation (PIANO_FUMO.md): features at the checkpoint, leave-one-agent-out, decision rules.
  python valuta_fumo.py controlla   builds the feature table WITHOUT outcomes (counts only), as a smoke test
  python valuta_fumo.py valuta      the evaluation; writes strumenti/risultati/fumo/fumo_risultati.json
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

TELLS = re.compile(r"\b(sorry|apologi[sz]e|my mistake|i made a mistake|wait|hmm|actually|oops|unfortunately|"
                   r"still (fail|not|doesn't|does not|isn't)|not working|doesn't work|didn't work|another approach|"
                   r"different approach|alternative approach|let me try|let's try|try again|try a different|"
                   r"i was wrong|confus\w*|it seems|seems like|strange|weird|unexpected)\b", re.I)
KINDS = ("read", "search", "edit", "run", "other")
VIEWPOINTS = {"B0": ["err_share"], "V1": ["rec_mean", "rec_trend", "ac1_rise"],
              "V2": ["nov_rate", "nov_late", "rep_max"], "V3": ["dist"], "V4": ["tell_rate"]}
NO_TEXT = {"claude_opus_4_5"}
RESULTS = os.path.join(fumo.OUT, "fumo_risultati.json")


def mean(xs):
    return sum(xs) / len(xs) if xs else 0.0


def ac1(x):
    """Lag-1 autocorrelation; 0 for series shorter than 3 or constant on either side."""
    if len(x) < 3:
        return 0.0
    a, b = x[:-1], x[1:]
    ma, mb = mean(a), mean(b)
    va = sum((u - ma) ** 2 for u in a)
    vb = sum((u - mb) ** 2 for u in b)
    if va == 0 or vb == 0:
        return 0.0
    return sum((u - ma) * (v - mb) for u, v in zip(a, b)) / math.sqrt(va * vb)


def checkpoint(lengths, share=0.3):
    xs = sorted(lengths)
    return max(4, round(share * xs[len(xs) // 2]))


def features(steps, K, agent):
    w = steps[:K]
    seen, nov = set(), []
    for s in w:
        nov.append(int(s["k"] not in seen))
        seen.add(s["k"])
    f = {"err_share": sum(s["e"] for s in w) / K}
    rec = []
    for i, s in enumerate(w):
        if s["e"]:
            j = next((j for j in range(i + 1, K) if nov[j]), None)
            rec.append((i, (j - i) if j is not None else (K - i)))
    half = K // 2
    first, second = [r for i, r in rec if i < half], [r for i, r in rec if i >= half]
    f["rec_mean"] = mean([r for _, r in rec])
    f["rec_trend"] = mean(second) - mean(first) if first and second else 0.0
    f["ac1_rise"] = ac1(nov[half:]) - ac1(nov[:half])
    f["nov_rate"] = mean(nov)
    f["nov_late"] = mean(nov[(2 * K) // 3:])
    f["rep_max"] = max(collections.Counter(s["k"] for s in w).values()) / K
    f["profile"] = [sum(s["t"] == k for s in w) / K for k in KINDS] + [mean([math.log1p(s["n"]) for s in w])]
    f["tell_rate"] = None if agent in NO_TEXT else sum(len(TELLS.findall(s["a"] or "")) for s in w) / K
    return f


def table(share=0.3):
    """One row per run still going after K steps: agent, failure (1/0), steps left, and the features. The profile
    distance uses each agent's own median and MAD over all its rows (no outcomes)."""
    by = collections.defaultdict(list)
    for r in fumo.load():
        by[r["agent"]].append(r)
    rows, ks = [], {}
    for agent, rs in sorted(by.items()):
        K = checkpoint([len(r["steps"]) for r in rs], share)
        ks[agent] = K
        alive = [r for r in rs if len(r["steps"]) > K]
        fs = [features(r["steps"], K, agent) for r in alive]
        prof = [f["profile"] for f in fs]
        dims = len(KINDS) + 1
        med = [sorted(p[i] for p in prof)[len(prof) // 2] for i in range(dims)]
        mad = [sorted(abs(p[i] - med[i]) for p in prof)[len(prof) // 2] * 1.4826 for i in range(dims)]
        for r, f in zip(alive, fs):
            zz = [(f["profile"][i] - med[i]) / max(mad[i], 0.05) for i in range(dims)]
            f["dist"] = math.sqrt(mean([v * v for v in zz]))
            rows.append({"agent": agent, "id": r["id"], "fail": int(r["outcome"] != "resolved"),
                         "left": len(r["steps"]) - K, **{k: v for k, v in f.items() if k != "profile"}})
    return rows, ks


def standardize(rows, cols):
    """z-score of every feature inside each agent, over all its rows (no outcomes used)."""
    out = {}
    for agent in sorted({r["agent"] for r in rows}):
        rs = [r for r in rows if r["agent"] == agent]
        for c in cols:
            vals = [r[c] for r in rs if r[c] is not None]
            if not vals:
                continue
            m, sd = float(np.mean(vals)), float(np.std(vals))
            for r in rs:
                if r[c] is not None:
                    out[(r["agent"], r["id"], c)] = (r[c] - m) / sd if sd > 0 else 0.0
    return out


def fit_logit(X, y, lam=1.0, iters=100):
    """L2-penalized logistic regression by Newton steps (intercept not penalized)."""
    Xb = np.hstack([np.ones((len(X), 1)), X])
    w = np.zeros(Xb.shape[1])
    reg = np.diag([0.0] + [lam] * X.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-Xb @ w))
        H = Xb.T @ (Xb * (p * (1 - p))[:, None]) + reg
        g = Xb.T @ (p - y) + reg @ w
        step = np.linalg.solve(H, g)
        w -= step
        if np.abs(step).max() < 1e-9:
            break
    return w


def auc(scores, y):
    """Probability that a failing run scores above a successful one (ties count half)."""
    pos = sorted(s for s, t in zip(scores, y) if t == 1)
    neg = sorted(s for s, t in zip(scores, y) if t == 0)
    if not pos or not neg:
        return None
    wins, j, k = 0.0, 0, 0
    for p in pos:
        while j < len(neg) and neg[j] < p:
            j += 1
        k = j
        while k < len(neg) and neg[k] == p:
            k += 1
        wins += j + 0.5 * (k - j)
    return wins / (len(pos) * len(neg))


def leave_one_out(rows, z, cols):
    """{held-out agent: (scores, y, threshold, steps left, weights)}; agents lacking a feature are skipped."""
    agents = sorted({r["agent"] for r in rows if all((r["agent"], r["id"], c) in z for c in cols)})
    out = {}
    for held in agents:
        train = [r for r in rows if r["agent"] in agents and r["agent"] != held]
        test = [r for r in rows if r["agent"] == held]
        X = np.array([[z[(r["agent"], r["id"], c)] for c in cols] for r in train])
        y = np.array([r["fail"] for r in train], dtype=float)
        w = fit_logit(X, y)
        s_train = np.hstack([np.ones((len(X), 1)), X]) @ w
        thr = float(np.quantile(s_train[y == 0], 0.98))
        Xt = np.array([[z[(r["agent"], r["id"], c)] for c in cols] for r in test])
        s = list(np.hstack([np.ones((len(Xt), 1)), Xt]) @ w)
        out[held] = (s, [r["fail"] for r in test], thr, [r["left"] for r in test], w.tolist())
    return out


def evaluate(share, label):
    rows, ks = table(share)
    cols = sorted({c for cs in VIEWPOINTS.values() for c in cs})
    z = standardize(rows, cols)
    res = {"label": label, "share": share, "checkpoint": ks,
           "runs": {a: {"alive": sum(r["agent"] == a for r in rows),
                        "fail": sum(r["fail"] for r in rows if r["agent"] == a)} for a in ks},
           "viewpoints": {}}
    scored = {name: leave_one_out(rows, z, cs) for name, cs in VIEWPOINTS.items()}
    scored["ALL_exploratory"] = leave_one_out(rows, z, [c for n, cs in VIEWPOINTS.items() if n != "V4" for c in cs])
    rng = random.Random(fumo.SEED)
    for name, per in scored.items():
        out = {}
        for agent, (s, y, thr, left, w) in per.items():
            stop = [v > thr for v in s]
            fails, succ = sum(y), len(y) - sum(y)
            entry = {"auc": auc(s, y),
                     "fail_catch": sum(st and t for st, t in zip(stop, y)) / fails if fails else None,
                     "success_loss": sum(st and not t for st, t in zip(stop, y)) / succ if succ else None,
                     "steps_saved_share": sum(l for st, t, l in zip(stop, y, left) if st and t) / max(1, sum(left)),
                     "weights": [round(x, 3) for x in w]}
            if name != "B0" and agent in scored["B0"]:
                b = scored["B0"][agent][0]
                diffs = []
                for _ in range(1000):
                    idx = [rng.randrange(len(y)) for _ in y]
                    yy = [y[i] for i in idx]
                    a1, a0 = auc([s[i] for i in idx], yy), auc([b[i] for i in idx], yy)
                    if a1 is not None and a0 is not None:
                        diffs.append(a1 - a0)
                diffs.sort()
                entry["auc_minus_B0"] = entry["auc"] - auc(b, y)
                entry["ci95"] = [round(diffs[int(0.025 * len(diffs))], 3), round(diffs[int(0.975 * len(diffs)) - 1], 3)]
            out[agent] = {k: (round(v, 3) if isinstance(v, float) else v) for k, v in entry.items()}
        res["viewpoints"][name] = out
    for name, out in res["viewpoints"].items():
        agents = [a for a in out if not a.startswith("_")]
        if name not in ("B0", "ALL_exploratory"):
            d = [out[a]["auc_minus_B0"] for a in agents]
            need = 2 if name == "V4" else 3
            out["_mean_auc_minus_B0"] = round(mean(d), 3)
            out["_promising"] = bool(d) and mean(d) >= 0.05 and sum(x > 0 for x in d) >= need
        hits = [a for a in agents if out[a]["fail_catch"] is not None and out[a]["fail_catch"] >= 0.5
                and out[a]["success_loss"] <= 0.02]
        out["_goal_agents"] = f"{len(hits)} of {len(agents)}"
        out["_goal_reached"] = len(hits) == len(agents)
    return res


def check():
    rows, ks = table(0.3)
    print("checkpoint", ks, "rows", len(rows), dict(collections.Counter(r["agent"] for r in rows)))


def run():
    res = {"main": evaluate(0.3, "principale"), "half_exploratory": evaluate(0.5, "esplorativo"),
           "code_sha256": {f: hashlib.sha256(open(os.path.join(fumo.HERE, f), "rb").read()).hexdigest()
                           for f in ("fumo.py", "valuta_fumo.py")}}
    with open(RESULTS, "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    m = res["main"]
    print("checkpoint", m["checkpoint"], "runs", m["runs"])
    for name, out in m["viewpoints"].items():
        print(name, {k: v for k, v in out.items() if k.startswith("_")})
        for a, v in out.items():
            if not a.startswith("_"):
                print("   ", a, {k: v[k] for k in ("auc", "auc_minus_B0", "ci95", "fail_catch", "success_loss",
                                                 "steps_saved_share") if k in v})


if __name__ == "__main__":
    {"controlla": check, "valuta": run}[sys.argv[1]]()
