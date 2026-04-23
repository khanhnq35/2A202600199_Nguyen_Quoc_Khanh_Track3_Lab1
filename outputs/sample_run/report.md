# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_eval.json
- Mode: ollama
- Records: 200
- Agents: react, reflexion

## Summary
| Metric | React | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.55 | 0.7 | 0.15 |
| Avg attempts | 1 | 1.8 | 0.8 |
| Avg token estimate | 484.39 | 739.17 | 254.78 |
| Avg latency (ms) | 10861.07 | 16331.44 | 5470.37 |

## Failure modes
```json
{
  "react": {
    "none": 73,
    "incomplete_multi_hop": 19,
    "wrong_final_answer": 8
  },
  "reflexion": {
    "none": 70,
    "looping": 20,
    "wrong_final_answer": 9,
    "incomplete_multi_hop": 1
  },
  "overall": {
    "none": 143,
    "incomplete_multi_hop": 20,
    "wrong_final_answer": 17,
    "looping": 20
  }
}
```

## Extensions implemented
- structured_evaluator
- reflection_memory
- benchmark_report_json
- mock_mode_for_autograding

## Discussion
This benchmark provides a rigorous comparison between a baseline ReAct agent and an advanced Reflexion agent, evaluated using a strict Exact Match (structured_evaluator) algorithm on 100 HotpotQA samples via a local Llama 3.2 (3B) model. The implementation of `reflection_memory` yielded a significant +15% absolute improvement in Exact Match (EM) accuracy (from 0.55 to 0.70). Analysis of failure modes reveals that Reflexion effectively mitigates the `incomplete_multi_hop` issue—reducing it from 19 occurrences in ReAct to just 1—demonstrating the agent's enhanced ability to follow complex reasoning chains to completion. However, this improvement requires a clear trade-off: Reflexion consumed approximately 50% more tokens (739 vs 484) and increased average latency (16.3s vs 10.8s) due to the overhead of evaluation and reflection cycles. Additionally, a prominent new failure mode emerged for the Reflexion agent: `looping` (20 occurrences). Despite receiving corrective strategies from the Reflector, the smaller 3B parameter model occasionally struggled to execute the suggested corrections, highlighting a fundamental limitation in instruction-following capabilities for smaller models during iterative self-correction loops.
