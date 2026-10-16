# Data and licences

| Source | Licence | What is here |
|---|---|---|
| SWE-bench Verified trajectories of three public OpenHands submissions (Qwen3-Coder 30B and 480B, Claude Opus 4.5), public bucket `swe-bench-submissions` | as published by the submitters | Gates 1-3 only: aggregate results (`strumenti/risultati/fumo/*.json`). No trajectory text is included. |
| SWE-bench Verified (`princeton-nlp/SWE-bench_Verified`, test split) | as published on Hugging Face | Not redistributed. Used for the true patches (gate 2) and issue texts (gate 3). |
| Gemma 4 E4B localization runs on the Kaggle Gemma 4 Developer Agent tasks | Apache-2.0 (my repository `clavis-systems/who-reads-the-code-map`) | Gate 1 only: aggregate results. |
| HumanEvalPack (`bigcode/humanevalpack`, Python) | MIT | Not redistributed as files. The agent logs of gates 4-5 (`strumenti/risultati/sogno/`) quote the buggy functions the agent read. |
| HumanEval+ (`evalplus/humanevalplus`) | Apache-2.0 | Not redistributed as files. Used for the strict tests of gates 7-10. |
| Gemma 4 E4B (`gemma4:e4b-it-qat`), Qwen3 8B (`qwen3:8b`) | model licences | Their outputs: the code Gemma wrote, its fixes, lessons and property checks, and the yes/no answers of both models. |

Not included: the compact step lists of gates 1-3 (they contain text from the third-party trajectories), the
internal-state vectors of gate 9 (19 MB, rebuilt by `mente.py leggi`), and the October HumanEvalFix run logs used as
"day 0" in gates 4-5 (their final fixes do appear, as code, in `strumenti/risultati/mercato/coppie.jsonl`).

My own code, texts and results are released under Apache-2.0 (`LICENSE`).
