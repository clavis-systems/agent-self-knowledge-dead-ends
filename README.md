# Ten dead ends: can a small AI agent tell when it is wrong?

In two days (15-16 October 2026) I tested ten ideas for one open problem: **can an AI coding agent tell, by itself or
with a small helper, that it is going wrong, before it hands in a wrong answer?** Companies running thousands of agent
jobs would pay for this: fewer wasted runs, fewer confident wrong fixes, a trustworthy "done".

Every idea went through a **quick gate**: a short test with its rule and threshold written down and committed to git
before I saw any result. If the gate stayed closed, I moved on. Nine gates stayed closed; the tenth (the dream) opened
its first step but then fell into the plan's grey zone and did no better than a placebo, and I did not widen it. I
publish them because a map of where the signal is *not* is useful to anyone working on the same problem, and because
negative results are rarely written down.

Author: Emanuele Rizzan, independent researcher (GitHub: clavis-systems).

## The ten gates

| # | Idea | Data | Gate (fixed before the data) | Result |
|---|---|---|---|---|
| 1 | **Smoke detector**: from outside, in the first 30% of a run, predict failure from the run's rhythm (slower recovery after errors, fewer new actions, distance from the agent's usual rhythm, apologies and second thoughts in its text) | 1,761 runs of 4 agents: Qwen3-Coder 30B and 480B and Claude Opus 4.5 on SWE-bench Verified (public OpenHands trajectories), Gemma 4 E4B on code localization | train on 3 agents, test on the 4th; stop half of the failing runs losing at most 2% of the successes | AUC 0.38-0.55, no better than counting errors; 0.42-0.61 even when trained and tested within one agent (exploratory) |
| 2 | **Arrival point** (cheating on purpose, with the true patch): did the agent reach a file the fix changes within the first 30%? | same runs + SWE-bench Verified patches | AUC at least 0.65 in 3 of 4 agents | 0.57-0.68, 1 of 4. Big agents find the right file early 84-97% of the time; they fail later, in the fix |
| 3 | **Smoke in the task**: predict failure from the issue text, before starting | 489 SWE-bench Verified tasks, 3 agents | mean AUC at least 0.70 | 0.56-0.62 (the human difficulty labels of SWE-bench Verified: 0.65-0.68) |
| 4 | **Instinct**: "emotions" measured by the host (unease: tests fail twice after an edit; boredom: repetition; fatigue: 12 of 20 calls used) as triggers for a reaction | 144 Gemma 4 E4B runs on HumanEvalFix | an emotion that fires in at least 10% of runs and marks at least 50% failures | unease is right half the time (5 of 10 runs end in failure) but fires in only 7% of runs; no emotion passes |
| 5 | **Dream**: after failing, the agent writes one lesson; lessons verified by a retry are kept for the next day | 13 failed tasks to dream on, 28 new tasks (14 failed before, 14 solved) | +4 rescued tasks over no lesson, at most 2 broken | same task: 8 vs 3 solved (first step open). New tasks: lessons +3 (grey zone, not widened), **and 8 generic tips I wrote without looking at any failure (a placebo added before the new-task runs) did +4**. On 14 tasks, one run each, the effect looks like "be careful", not learning |
| 6 | **Market of thoughts**: small voices (Gemma 4 E4B, Qwen3 8B) bet yes/no on whether a finished fix is correct; their market should beat each voice | 206 Gemma fixes with hidden-test outcomes | market at least 0.03 AUC above the best voice, and adds 0.03 to running the visible tests | voices 0.78 and 0.81, market 0.82 (0.78 with learned weights); running the visible tests alone: 0.88, tests plus voices: 0.94 |
| 7 | **Second look with fresh eyes**: does the judge catch the false "done" (visible tests pass, strict tests fail)? | 507 solutions that pass the visible tests, 40 of them wrong on HumanEval+ | Gemma's judge AUC at least 0.75 | 0.725 (Qwen 0.77). A promising 0.88 the day before came from only 9 cases |
| 8 | **Self-built sense**: when in doubt, the agent writes property checks from the docstring only and runs them | same 507 solutions | catch half of the false "done" with at most 10% false alarms | catches 20 of 40, but flags 34% of the good solutions: the checks themselves are often wrong |
| 9 | **Mind reading**: a probe on the model's internal state (last layer, read with llama.cpp) instead of its yes/no | same solutions, Qwen3 8B | probe at least 0.05 AUC above the verbal judge | probe 0.61 (0.50-0.72 in an independent check with many variants) vs words 0.77 |
| 10 | **Hive**: use luck; retry only where there is doubt (visible tests fail or the judge doubts) | 3 recorded attempts for each of 163 HumanEval functions | catch 80% of the luck ceiling with at most 1.6 attempts, and beat plain "retry when the visible tests fail" by 2 points | 143 of 163, exactly like plain retry (143 with 1.28 attempts), but with 1.68 attempts (counting 6 doubtful items more strictly, every number drops by 6; same conclusion) |

## What I take from it

1. **Early in a run there is little to see.** Not in the rhythm of the actions, and little even in whether the agent
   has already found the right file. Failure is decided late, when the agent writes the fix.
2. **Failure is mostly a property of the task.** On the same 500 tasks, when Qwen3-Coder 30B succeeds, its 480B
   sibling fails only 4% of the time; when the 30B fails, the 480B fails 58% of the time (an exploratory count). But I
   could not read this difficulty from the issue text with simple text features.
3. **The self-knowledge of small models plateaus around 0.6-0.8 AUC**, whether it is asked in words, written as its
   own checks, or read from its internal state.
4. **The dumb control was the strongest single signal everywhere I measured it.** Running the visible tests, and
   retrying when they fail, beat or matched every clever organ on its own; the voices added only a little on top of the
   tests (0.88 to 0.94). In software, tests are the strongest sense an agent has.
5. **Controls saved me twice from a false discovery.** Without the placebo, "the AI learns from its dreams" would have
   looked true; without waiting for 40 cases, "a fresh look catches false done at 0.88" would have looked true.
6. **Luck is large for agents, small for single functions.** Rerunning the same bug-fixing agent solved 6 of 14 tasks
   it had failed (Ollama on a GPU does not repeat itself exactly); when writing small functions, retrying gained at
   most 8 of 163.

## How the gates were run

- Each idea has a plan (`PIANO_*.md`, in Italian, my language) committed before any result, and a result file
  (`RISULTATO_*.md`). Changes after the plan are declared in the plan's "Scostamenti" section.
- The main numbers of every gate were recounted or recomputed by a separate AI agent with its own code, from the raw
  files. The result files say exactly what was checked; not rechecked: the text models of gate 3 (only the human
  difficulty reference was) and the full leave-one-agent-out models of gate 1 (its raw indicators were).
- The commit ids cited in the plan and result files belong to my private working repository; the files here are
  copies of the committed versions.
- All model-generated code and all test code ran only in a WebAssembly sandbox, never directly on my PC.
- Models ran locally on a laptop GPU (RTX 5060, 8 GB) with Ollama 0.32.13: Gemma 4 E4B (`gemma4:e4b-it-qat`) and
  Qwen3 8B (`qwen3:8b`). Mind reading used llama.cpp on the same Qwen3 file.

## What is in this repository

| Folder | Content |
|---|---|
| `strumenti/agenti/fumo/` | Gates 1-3: code, plans, results |
| `strumenti/agenti/sogno/` | Gates 4-5 |
| `strumenti/agenti/mercato/`, `sguardo/`, `senso/`, `mente/`, `alveare/` | Gates 6-10 |
| `strumenti/agenti/modifiche/`, `strumenti/valutazione/` | The Gemma bug-fixing agent and the WebAssembly sandbox they use |
| `strumenti/risultati/` | Summaries of every gate and the per-item data of gates 5-8 and 10 (outcomes, judge scores, the code Gemma wrote) |
| `DATA.md` | Where the data come from, licences, what is not included |

## Limits

Quick gates are screening tests, not final answers: a closed gate says "not like this, not with this data". The models
are small and local; the code tasks are small Python functions (HumanEval, HumanEvalFix) plus SWE-bench trajectories
of three public agents; mind reading used only the last layer of one model; most gates use a few hundred items.

## Use of AI

I chose the questions and directed every test. Claude (Anthropic) wrote the code and ran the analyses under my
direction, and separate Claude agents recounted the results. The bug-fixing agent reused from an earlier study had
been reviewed by OpenAI Codex. Gemma 4 E4B and Qwen3 8B are the models under test.
