from __future__ import annotations
import json
from pathlib import Path
import typer
from rich import print
from src.reflexion_lab.agents import ReActAgent, ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
app = typer.Typer(add_completion=False)

@app.command()
def main(dataset: str = "data/hotpot_mini.json", out_dir: str = "outputs/sample_run", reflexion_attempts: int = 3) -> None:
    examples = load_dataset(dataset)
    react = ReActAgent()
    reflexion = ReflexionAgent(max_attempts=reflexion_attempts)
    
    react_records = []
    reflexion_records = []
    
    print(f"[bold green]Starting Benchmark on {len(examples)} examples...[/bold green]")
    
    for i, example in enumerate(examples, 1):
        print(f"\n[bold white on blue] QUESTION {i}/{len(examples)}: {example.question} [/bold white on blue]")
        
        # Chạy ReAct
        react_rec = react.run(example)
        react_records.append(react_rec)
        
        # Chạy Reflexion
        reflexion_rec = reflexion.run(example)
        reflexion_records.append(reflexion_rec)

    all_records = react_records + reflexion_records
    out_path = Path(out_dir)
    save_jsonl(out_path / "react_runs.jsonl", react_records)
    save_jsonl(out_path / "reflexion_runs.jsonl", reflexion_records)
    report = build_report(all_records, dataset_name=Path(dataset).name, mode="ollama")
    json_path, md_path = save_report(report, out_path)
    print(f"[green]Saved[/green] {json_path}")
    print(f"[green]Saved[/green] {md_path}")
    print(json.dumps(report.summary, indent=2))

if __name__ == "__main__":
    app()
