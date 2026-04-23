import json
import os
from pathlib import Path
import typer
from rich import print
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

from src.reflexion_lab.agents import ReflexionAgent
from src.reflexion_lab.reporting import build_report, save_report
from src.reflexion_lab.utils import load_dataset, save_jsonl
from src.reflexion_lab.schemas import RunRecord

app = typer.Typer(add_completion=False)

def load_saved_records(jsonl_path: str) -> list[RunRecord]:
    """Tải lại kết quả đã chạy từ file JSONL"""
    records = []
    if not os.path.exists(jsonl_path):
        return []
    with open(jsonl_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                records.append(RunRecord(**json.loads(line)))
    return records

@app.command()
def main(
    dataset: str = "data/hotpot_eval.json", 
    out_dir: str = "outputs/eval_run_v2", 
    old_react_path: str = "outputs/eval_run/react_runs.jsonl"
):
    examples = load_dataset(dataset)
    reflexion = ReflexionAgent(max_attempts=3)
    reflexion_records = []
    
    print(f"[bold green]🚀 Bắt đầu chạy Reflexion V2 (Cải tiến) trên {len(examples)} câu hỏi...[/bold green]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        transient=False,
    ) as progress:
        task_ref = progress.add_task("[magenta]Running Reflexion V2...", total=len(examples))
        for ex in examples:
            record = reflexion.run(ex)
            # Đổi tên agent để dễ so sánh trong report
            record.agent_type = "reflexion_v2"
            reflexion_records.append(record)
            
            status = "[green]CORRECT[/green]" if record.is_correct else f"[red]WRONG[/red] ({record.failure_mode})"
            progress.console.log(f"Reflexion V2 - QID {ex.qid}: {status} - Attempts: {record.attempts}")
            progress.update(task_ref, advance=1)
            
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    save_jsonl(out_path / "reflexion_v2_runs.jsonl", reflexion_records)
    print(f"\n[bold green]✅ Đã lưu kết quả Reflexion V2 tại {out_dir}/reflexion_v2_runs.jsonl[/bold green]")
    
    # TIẾN HÀNH LOAD KẾT QUẢ CŨ ĐỂ SO SÁNH
    print(f"\n[bold yellow]🔍 Đang tìm kết quả ReAct cũ tại: {old_react_path}...[/bold yellow]")
    react_records = load_saved_records(old_react_path)
    
    if len(react_records) > 0:
        print(f"[bold green]🎉 Tìm thấy {len(react_records)} bản ghi ReAct! Tiến hành gộp Report...[/bold green]")
        all_records = react_records + reflexion_records
        report = build_report(all_records, dataset_name=Path(dataset).name, mode="ollama")
        json_path, md_path = save_report(report, out_path)
        print(f"[bold cyan]📊 Report so sánh cuối cùng đã được tạo: {md_path}[/bold cyan]")
    else:
        print(f"[bold red]⚠️ Chưa tìm thấy file ReAct cũ. Có thể luồng kia chưa chạy xong![/bold red]")
        print("[dim]Không sao cả, kết quả Reflexion V2 của bạn đã được lưu an toàn. Khi nào luồng cũ chạy xong, bạn chỉ cần chạy lại file này một lần nữa (nó sẽ load cả hai)![/dim]")

if __name__ == "__main__":
    app()
