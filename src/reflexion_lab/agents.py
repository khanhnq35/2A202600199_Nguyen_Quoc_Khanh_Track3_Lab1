from __future__ import annotations
from dataclasses import dataclass
from typing import Literal
from .llm_runtime import actor_answer, evaluator, reflector
from .schemas import AttemptTrace, QAExample, ReflectionEntry, RunRecord
from rich.console import Console

console = Console()

@dataclass
class BaseAgent:
    agent_type: Literal["react", "reflexion"]
    max_attempts: int = 1
    def run(self, example: QAExample) -> RunRecord:
        reflection_memory: list[str] = []
        reflections: list[ReflectionEntry] = []
        traces: list[AttemptTrace] = []
        final_answer = ""
        final_score = 0
        for attempt_id in range(1, self.max_attempts + 1):
            console.print(f"\n[bold blue]─── {self.agent_type.upper()} Attempt {attempt_id} ───[/bold blue]")
            
            answer, act_tok, act_lat = actor_answer(example, attempt_id, self.agent_type, reflection_memory)
            console.print(f"[dim]Actor Answer:[/dim] [yellow]{answer}[/yellow]")
            
            judge, eval_tok, eval_lat = evaluator(example, answer)
            
            token_estimate = act_tok + eval_tok
            latency_ms = act_lat + eval_lat
            
            trace = AttemptTrace(
                attempt_id=attempt_id, 
                answer=answer, 
                score=judge.score, 
                reason=judge.reason, 
                token_estimate=token_estimate, 
                latency_ms=latency_ms
            )
            final_answer = answer
            final_score = judge.score
            
            if judge.score == 1:
                console.print(f"[bold green]✓ Correct![/bold green] (Reason: {judge.reason})")
                traces.append(trace)
                break
            else:
                console.print(f"[bold red]✗ Incorrect[/bold red] (Reason: {judge.reason})")
            
            # Logic Reflexion: Gọi reflector nếu sai và chưa hết attempts
            if self.agent_type == "reflexion" and attempt_id < self.max_attempts:
                ref_entry, ref_tok, ref_lat = reflector(example, attempt_id, judge)
                console.print(f"[bold magenta]↺ Reflection:[/bold magenta] {ref_entry.failure_reason}")
                console.print(f"[bold cyan]💡 Strategy:[/bold cyan] {ref_entry.next_strategy}")
                
                reflection_memory.append(ref_entry.next_strategy)
                reflections.append(ref_entry)
                trace.reflection = ref_entry
                trace.token_estimate += ref_tok
                trace.latency_ms += ref_lat
                
            traces.append(trace)
            
        total_tokens = sum(t.token_estimate for t in traces)
        total_latency = sum(t.latency_ms for t in traces)
        
        # Phân loại failure mode dựa trên kết quả các attempt
        if final_score == 1:
            failure_mode = "none"
        elif len(traces) > 1 and traces[-1].answer == traces[-2].answer:
            failure_mode = "looping"
        elif any(final_answer.lower() in c.text.lower() for c in example.context) and final_answer.lower() != example.gold_answer.lower():
            failure_mode = "incomplete_multi_hop"
        elif len(final_answer.split()) > 10:
            failure_mode = "entity_drift"
        else:
            failure_mode = "wrong_final_answer"
            
        return RunRecord(
            qid=example.qid, 
            question=example.question, 
            gold_answer=example.gold_answer, 
            agent_type=self.agent_type, 
            predicted_answer=final_answer, 
            is_correct=bool(final_score), 
            attempts=len(traces), 
            token_estimate=total_tokens, 
            latency_ms=total_latency, 
            failure_mode=failure_mode, 
            reflections=reflections, 
            traces=traces
        )

class ReActAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(agent_type="react", max_attempts=1)

class ReflexionAgent(BaseAgent):
    def __init__(self, max_attempts: int = 3) -> None:
        super().__init__(agent_type="reflexion", max_attempts=max_attempts)
