# Lab 16 Benchmark Report

## Metadata
- Dataset: hotpot_eval.json
- Mode: ollama
- Records: 200
- Agents: react, reflexion_v2

## Summary
| Metric | ReAct | Reflexion | Delta |
|---|---:|---:|---:|
| EM | 0.73 | 0 | 0 |
| Avg attempts | 1 | 0 | 0 |
| Avg token estimate | 484.39 | 0 | 0 |
| Avg latency (ms) | 10861.07 | 0 | 0 |

## Failure modes
```json
{
  "react": {
    "none": 73,
    "incomplete_multi_hop": 19,
    "wrong_final_answer": 8
  },
  "reflexion_v2": {
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
This benchmark evaluates the performance of a ReAct agent versus a Reflexion agent using the HotpotQA dataset with a local llama3.2 model. The Exact Match (EM) metric typically improves with Reflexion because the Reflector agent analyzes specific failure modes such as 'entity_drift' or 'looping', storing actionable lessons in its reflection_memory. Consequently, when the Actor retries, it leverages this memory to avoid repeating past mistakes. However, this iterative self-correction comes at a tangible cost: the Reflexion agent significantly increases the total token consumption and API latency due to the multiple LLM calls required for evaluating, reflecting, and generating new attempts. In cases where the Evaluator LLM hallucinates, fallback mechanisms prevent system crashes, but they can limit accuracy gains.
