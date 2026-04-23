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
                data = json.loads(line)
                # Fix lỗi Pydantic Literal: Chuyển reflexion_v2 về reflexion
                if data.get("agent_type") == "reflexion_v2":
                    data["agent_type"] = "reflexion"
                records.append(RunRecord(**data))
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
    
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    v2_save_path = out_path / "reflexion_v2_runs.jsonl"
    
    # THỬ LOAD KẾT QUẢ REFLEXION V2 ĐÃ CÓ SẴN ĐỂ TIẾT KIỆM THỜI GIAN
    print(f"\n[bold yellow]🔍 Đang kiểm tra kết quả Reflexion V2 đã chạy tại: {v2_save_path}...[/bold yellow]")
    reflexion_records = load_saved_records(str(v2_save_path))
    
    if len(reflexion_records) >= len(examples):
        print(f"[bold green]✨ Đã tìm thấy đủ {len(reflexion_records)} kết quả Reflexion V2. Bỏ qua việc chạy lại LLM![/bold green]")
    else:
        print(f"[bold green]🚀 Bắt đầu chạy Reflexion V2 (Cải tiến) cho {len(examples) - len(reflexion_records)} câu còn lại...[/bold green]")
        
        # Chỉ lấy những ví dụ chưa có trong records
        processed_qids = {r.qid for r in reflexion_records}
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            transient=False,
        ) as progress:
            task_ref = progress.add_task("[magenta]Running Reflexion V2...", total=len(examples))
            progress.update(task_ref, completed=len(reflexion_records))
            
            for ex in examples:
                if ex.qid in processed_qids:
                    continue
                    
                record = reflexion.run(ex)
                record.agent_type = "reflexion"
                reflexion_records.append(record)
                
                status = "[green]CORRECT[/green]" if record.is_correct else f"[red]WRONG[/red] ({record.failure_mode})"
                progress.console.log(f"Reflexion V2 - QID {ex.qid}: {status} - Attempts: {record.attempts}")
                progress.update(task_ref, advance=1)
                
        save_jsonl(v2_save_path, reflexion_records)
        print(f"\n[bold green]✅ Đã lưu/cập nhật kết quả Reflexion V2 tại {v2_save_path}[/bold green]")
    
    # TIẾN HÀNH LOAD KẾT QUẢ CŨ ĐỂ SO SÁNH
    print(f"\n[bold yellow]🔍 Đang tìm kết quả ReAct cũ tại: {old_react_path}...[/bold yellow]")
    react_records = load_saved_records(old_react_path)
    
    if len(react_records) > 0:
        print(f"[bold green]🎉 Tìm thấy {len(react_records)} bản ghi ReAct! Đang chuẩn hóa điểm số để so sánh công bằng...[/bold green]")
        # Chấm điểm lại ReAct bằng bộ chấm mới (Exact Match) để so sánh công bằng
        from src.reflexion_lab.llm_runtime import evaluator
        from src.reflexion_lab.schemas import QAExample
        
        for rec in react_records:
            mock_ex = QAExample(qid=rec.qid, question=rec.question, gold_answer=rec.gold_answer, context=[], difficulty="medium")
            judge, _, _ = evaluator(mock_ex, rec.predicted_answer)
            rec.is_correct = (judge.score == 1)

        all_records = react_records + reflexion_records
        report = build_report(all_records, dataset_name=Path(dataset).name, mode="ollama")
        json_path, md_path = save_report(report, out_path)
        print(f"[bold cyan]📊 Report so sánh công bằng đã được tạo: {md_path}[/bold cyan]")
    else:
        print(f"[bold red]⚠️ Chưa tìm thấy file ReAct cũ. Có thể luồng kia chưa chạy xong![/bold red]")
        print("[dim]Không sao cả, kết quả Reflexion V2 của bạn đã được lưu an toàn. Khi nào luồng cũ chạy xong, bạn chỉ cần chạy lại file này một lần nữa (nó sẽ load cả hai)![/dim]")

if __name__ == "__main__":
    app()
