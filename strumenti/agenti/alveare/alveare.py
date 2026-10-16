"""L'alveare (PIANO_ALVEARE.md): retry policies simulated on the 3 recorded attempts per HumanEval task (sguardo B).
  python alveare.py     prints and saves the policies' results and the gate decision (CPU only, no model)
"""
import hashlib
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
SG = os.path.join(ROOT, "strumenti", "risultati", "sguardo")
OUT = os.path.join(ROOT, "strumenti", "risultati", "alveare")


def attempts():
    """{task: [attempt for seed 1, 2, 3]}; an attempt is {visible, strict, judge} (no code = failed, no judge)."""
    with open(os.path.join(SG, "canonical_ok.json"), encoding="utf-8") as fh:
        canon = {int(k): v for k, v in json.load(fh).items()}
    labels, judge = {}, {}
    with open(os.path.join(SG, "etichette.jsonl"), encoding="utf-8") as fh:
        for x in map(json.loads, fh):
            if x["part"] == "B":
                labels[x["pid"]] = x
    with open(os.path.join(SG, "giudizi_gemma.jsonl"), encoding="utf-8") as fh:
        judge = {a["pid"]: a["score"] for a in map(json.loads, fh)}
    out = {}
    with open(os.path.join(SG, "generati.jsonl"), encoding="utf-8") as fh:
        for g in map(json.loads, fh):
            if canon.get(g["task"]) != 1:
                continue
            if g["code"]:
                pid = f"B{g['task']}_{hashlib.sha256(g['code'].encode()).hexdigest()[:10]}"
                lab = labels[pid]
                a = {"seed": g["seed"], "visible": lab["visible_pass"] == 1, "strict": lab["strict_pass"] == 1,
                     "judge": judge.get(pid)}
            else:
                a = {"seed": g["seed"], "visible": False, "strict": False, "judge": None}
            out.setdefault(g["task"], []).append(a)
    for t in out:
        out[t].sort(key=lambda a: a["seed"])
        assert [a["seed"] for a in out[t]] == [1, 2, 3], t
    return out


def doubt_threshold(tasks):
    scores = sorted(a["judge"] for ats in tasks.values() for a in ats if a["visible"] and a["judge"] is not None)
    return scores[int(0.25 * len(scores))]


def p1(ats, thr):
    return ats[0]["strict"], 1


def retry_visible(ats, thr):
    for i, a in enumerate(ats):
        if a["visible"]:
            return a["strict"], i + 1
    return ats[0]["strict"], 3


def hive(ats, thr):
    for i, a in enumerate(ats):
        if a["visible"] and a["judge"] is not None and a["judge"] >= thr:
            return a["strict"], i + 1
    vis = [a for a in ats if a["visible"]]
    if vis:
        best = max(vis, key=lambda a: a["judge"] if a["judge"] is not None else float("-inf"))
        return best["strict"], 3
    return ats[0]["strict"], 3


def always3(ats, thr):
    for a in ats:
        if a["visible"]:
            return a["strict"], 3
    return ats[0]["strict"], 3


def oracle(ats, thr):
    return any(a["strict"] for a in ats), 3


def main():
    tasks = attempts()
    thr = doubt_threshold(tasks)
    res = {"tasks": len(tasks), "doubt_threshold": round(thr, 4), "policies": {}}
    for name, pol in (("P1", p1), ("V_retry_if_visible_fails", retry_visible), ("ALVEARE", hive), ("P3", always3),
                      ("ORACOLO", oracle)):
        outs = [pol(ats, thr) for ats in tasks.values()]
        res["policies"][name] = {"solved": sum(s for s, _ in outs), "rate": round(sum(s for s, _ in outs) / len(outs), 4),
                                 "mean_attempts": round(sum(c for _, c in outs) / len(outs), 3)}
    P = res["policies"]
    ceiling = P["ORACOLO"]["rate"] - P["P1"]["rate"]
    for name in ("V_retry_if_visible_fails", "ALVEARE", "P3"):
        P[name]["capture_of_luck_ceiling"] = round((P[name]["rate"] - P["P1"]["rate"]) / ceiling, 3) if ceiling > 0 else None
    alv, v = P["ALVEARE"], P["V_retry_if_visible_fails"]
    res["gate"] = {"1_capture_ge_0.80_with_le_1.6_attempts": (alv["capture_of_luck_ceiling"] or 0) >= 0.80 and alv["mean_attempts"] <= 1.6,
                   "2_beats_dumb_control_by_2_points": alv["rate"] - v["rate"] >= 0.02}
    res["gate"]["passes"] = all(res["gate"].values())
    res["code_sha256"] = hashlib.sha256(open(os.path.abspath(__file__), "rb").read()).hexdigest()
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, "alveare_risultati.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
