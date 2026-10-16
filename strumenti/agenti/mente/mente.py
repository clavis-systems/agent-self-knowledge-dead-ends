"""Leggere nella mente (PIANO_MENTE.md): a probe on the internal state of Qwen3 8B, read with llama.cpp from the same
GGUF file Ollama uses, against the verbal yes/no judgement of the same model.
  python mente.py leggi VOICE     GPU: llama-server --embeddings --pooling last; vectors of the judge text and of the
                                  code alone, for the 597 labelled solutions (needs Ollama stopped)
  python mente.py valuta VOICE    probe with 5 task-grouped folds; gate decision
"""
import json
import os
import random
import subprocess
import sys
import time
import urllib.request

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "sguardo")))
import sguardo as sg  # noqa: E402

mk, ag, vf = sg.mk, sg.ag, sg.vf
ROOT = ag.ROOT
OUT = os.path.join(ROOT, "strumenti", "risultati", "mente")
SERVER = os.path.join(ROOT, "llama.cpp", "llama-server.exe")
BLOBS = {"qwen": "sha256-a3de86cd1c13", "gemma": "sha256-e8b6a059ba86"}
PORT = 8091
SEED = "mente-2026-10-16"
COMPONENTS, LAM = 50, 1.0


def blob(voice):
    folder = os.path.join(os.path.expanduser("~"), ".ollama", "models", "blobs")
    hits = [f for f in os.listdir(folder) if f.startswith(BLOBS[voice])]
    if len(hits) != 1:
        raise SystemExit(f"model file not found for {voice}")
    return os.path.join(folder, hits[0])


def labelled():
    with open(os.path.join(sg.OUT, "canonical_ok.json"), encoding="utf-8") as fh:
        canon = {int(k): v for k, v in json.load(fh).items()}
    with open(sg.LABELS, encoding="utf-8") as fh:
        return [x for x in map(json.loads, fh) if canon.get(x["task"]) == 1 and x["strict_pass"] in (0, 1)]


def embed(text):
    body = {"input": text, "model": "local"}
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/v1/embeddings", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        return json.load(r)["data"][0]["embedding"]


def read(voice):
    os.makedirs(OUT, exist_ok=True)
    rows, labs = ag.load_rows(), labelled()
    proc = subprocess.Popen([SERVER, "-m", blob(voice), "--embeddings", "--pooling", "last", "-c", "6144",
                             "-ngl", "99", "--port", str(PORT), "--host", "127.0.0.1"],
                            stdout=subprocess.DEVNULL, stderr=open(os.path.join(OUT, f"server_{voice}.log"), "w"))
    try:
        for _ in range(120):
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/health", timeout=5) as r:
                    if json.load(r).get("status") == "ok":
                        break
            except OSError:
                time.sleep(2)
        else:
            raise SystemExit("llama-server did not start")
        full, code_only = [], []
        for i, x in enumerate(labs):
            q = mk.QUESTION.format(spec=rows[x["task"]]["prompt"].strip(), code=x["code"])
            full.append(embed(q))
            code_only.append(embed(x["code"]))
            if i % 100 == 0:
                print(i, len(labs), flush=True)
        np.save(os.path.join(OUT, f"{voice}_full.npy"), np.array(full, dtype=np.float32))
        np.save(os.path.join(OUT, f"{voice}_code.npy"), np.array(code_only, dtype=np.float32))
        with open(os.path.join(OUT, f"{voice}_order.json"), "w", encoding="utf-8") as fh:
            json.dump([x["pid"] for x in labs], fh)
    finally:
        proc.terminate()
        proc.wait(timeout=30)
    print(voice, "read", len(labs))


def probe_scores(X, y, groups, permute=False):
    keys = sorted(set(groups))
    random.Random(SEED).shuffle(keys)
    fold = {k: i % 5 for i, k in enumerate(keys)}
    rng = np.random.default_rng(1)
    s = np.zeros(len(y))
    for f in range(5):
        tr = np.array([i for i, g in enumerate(groups) if fold[g] != f])
        te = np.array([i for i, g in enumerate(groups) if fold[g] == f])
        mu, sd = X[tr].mean(0), X[tr].std(0)
        sd[sd == 0] = 1
        A = (X[tr] - mu) / sd
        _, _, vt = np.linalg.svd(A, full_matrices=False)
        P = vt[:COMPONENTS].T
        ytr = y[tr].copy()
        if permute:
            rng.shuffle(ytr)
        w = vf.fit_logit(A @ P, ytr, lam=LAM)
        B = ((X[te] - mu) / sd) @ P
        s[te] = np.hstack([np.ones((len(te), 1)), B]) @ w
    return s


def evaluate(voice):
    labs = labelled()
    with open(os.path.join(OUT, f"{voice}_order.json"), encoding="utf-8") as fh:
        order = json.load(fh)
    assert order == [x["pid"] for x in labs], "labels changed since the vectors were read"
    full = np.load(os.path.join(OUT, f"{voice}_full.npy"))
    code = np.load(os.path.join(OUT, f"{voice}_code.npy"))
    y = np.array([x["strict_pass"] for x in labs], dtype=float)
    groups = [x["task"] for x in labs]
    pool = np.array([x["visible_pass"] == 1 for x in labs])
    verbal = {}
    for path in (os.path.join(mk.OUT, f"risposte_{voice}.jsonl"), os.path.join(sg.OUT, f"giudizi_{voice}.jsonl")):
        with open(path, encoding="utf-8") as fh:
            verbal.update({a["pid"]: a["score"] for a in map(json.loads, fh)})
    v = np.array([verbal.get(x["pid"], np.nan) for x in labs])
    a = lambda s: round(vf.auc(list(s[pool]), list(y[pool])), 3)
    s_full = probe_scores(full, y, groups)
    z = lambda t: (t - np.nanmean(t)) / (np.nanstd(t) or 1)
    combo = z(s_full) + np.nan_to_num(z(v))                       # exploratory: plain sum of the two z-scores
    res = {"voice": voice, "solutions": len(labs), "pool": int(pool.sum()), "false_done": int((y[pool] == 0).sum()),
           "auc_pool": {"probe_internal_state": a(s_full), "verbal_yes_no": a(v),
                        "probe_plus_verbal_exploratory": a(combo),
                        "control_code_only": a(probe_scores(code, y, groups)),
                        "control_permuted_labels": a(probe_scores(full, y, groups, permute=True)),
                        "control_length": a(np.array([-np.log1p(len(x["code"])) for x in labs]))}}
    res["gate"] = {"probe_beats_verbal_by_0.05": res["auc_pool"]["probe_internal_state"] >= res["auc_pool"]["verbal_yes_no"] + 0.05}
    res["gate"]["passes"] = res["gate"]["probe_beats_verbal_by_0.05"]
    with open(os.path.join(OUT, f"mente_risultati_{voice}.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, ensure_ascii=False, indent=1)
    print(json.dumps(res, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    {"leggi": lambda: read(sys.argv[2]), "valuta": lambda: evaluate(sys.argv[2])}[sys.argv[1]]()
