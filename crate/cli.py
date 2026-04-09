"""
crate — DJ-ready audio analysis CLI

Commands:
  analyze   BPM + key detection and tag writing
  stems     Stem separation with Demucs
  full      Both of the above in one shot
"""
from pathlib import Path
from typing import Annotated, Optional

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
from rich.table import Table

from .analyzer import analyze
from .scanner import scan_folder
from .stems import MODELS, extract_stems
from .tagger import write_tags

app = typer.Typer(
    name="crate",
    help="DJ-ready audio analysis for Serato DJ Pro and Rekordbox.",
    no_args_is_help=True,
    pretty_exceptions_enable=False,
)
console = Console()

_FolderArg = Annotated[Path, typer.Argument(help="Folder containing audio files")]
_ModeOpt = Annotated[
    str,
    typer.Option("--mode", "-m", help="Tag mode: serato | rekordbox | both"),
]
_RecursiveOpt = Annotated[bool, typer.Option("--recursive", "-r", help="Scan subfolders")]
_DryRunOpt = Annotated[bool, typer.Option("--dry-run", help="Analyse without writing tags")]


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

_OutputOpt = Annotated[
    Optional[Path],
    typer.Option("--output", "-o", help="Destination folder for tagged copies (omit to tag in place)"),
]


@app.command("analyze")
def analyze_cmd(
    folder: _FolderArg,
    output: _OutputOpt = None,
    mode: _ModeOpt = "both",
    recursive: _RecursiveOpt = True,
    dry_run: _DryRunOpt = False,
) -> None:
    """Detect BPM and musical key for every audio file in FOLDER, then write DJ-ready tags."""
    _require_folder(folder)

    files = scan_folder(folder, recursive=recursive)
    if not files:
        console.print(f"[yellow]No audio files found in[/yellow] {folder}")
        raise typer.Exit(0)

    dest_note = f" → [cyan]{output}[/cyan]" if output else " [dim](in place)[/dim]"
    console.print(f"\n[bold]Found {len(files)} audio file(s)[/bold] in [cyan]{folder}[/cyan]{dest_note}\n")

    table = Table(show_header=True, header_style="bold magenta", expand=False)
    table.add_column("File", style="cyan", max_width=42)
    table.add_column("BPM", justify="right", style="green")
    table.add_column("Key", justify="center")
    table.add_column("Camelot", justify="center", style="yellow")
    table.add_column("Confidence", justify="right")
    table.add_column("Status", justify="center")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console,
        transient=True,
    ) as progress:
        task = progress.add_task("Analysing...", total=len(files))

        for path in files:
            progress.update(task, description=f"Analysing [cyan]{path.name}[/cyan]")
            try:
                result = analyze(path)
                if not dry_run:
                    write_tags(path, result, mode=mode, output_root=output, source_root=folder)
                    status = "[green]Copied & tagged[/green]" if output else "[green]Tagged[/green]"
                else:
                    status = "[blue]Dry run[/blue]"

                table.add_row(
                    path.name,
                    f"{result.bpm:.1f}",
                    result.key,
                    result.camelot,
                    f"{result.confidence:.3f}",
                    status,
                )
            except Exception as exc:  # noqa: BLE001
                table.add_row(path.name, "-", "-", "-", "-", f"[red]{exc}[/red]")

            progress.advance(task)

    console.print(table)

    if not dry_run:
        action = f"Copies written to [cyan]{output}[/cyan]" if output else "Files tagged in place"
        console.print(f"\n[bold green]Done.[/bold green] {action} in [bold]{mode}[/bold] mode.\n")
    else:
        console.print("\n[bold blue]Dry run complete — no files were modified.[/bold blue]\n")


# ---------------------------------------------------------------------------
# stems
# ---------------------------------------------------------------------------

@app.command("stems")
def stems_cmd(
    folder: _FolderArg,
    output: Annotated[
        Optional[Path],
        typer.Option("--output", "-o", help="Output directory for stems (default: <folder>/stems)"),
    ] = None,
    model: Annotated[
        str,
        typer.Option("--model", help=f"Separation model: {' | '.join(MODELS)}"),
    ] = "4stems",
    device: Annotated[
        str,
        typer.Option("--device", help="Inference device: cpu | cuda | mps"),
    ] = "cpu",
    recursive: _RecursiveOpt = False,
) -> None:
    """Separate audio files into stems (vocals, drums, bass, other) using Demucs."""
    _require_folder(folder)

    files = scan_folder(folder, recursive=recursive)
    if not files:
        console.print(f"[yellow]No audio files found in[/yellow] {folder}")
        raise typer.Exit(0)

    out_dir = output or folder / "stems"
    console.print(
        f"\n[bold]Extracting stems for {len(files)} file(s)[/bold]\n"
        f"Model: [yellow]{model}[/yellow]  |  Device: [yellow]{device}[/yellow]  |  "
        f"Output: [cyan]{out_dir}[/cyan]\n"
    )

    for i, path in enumerate(files, 1):
        console.print(f"  [[bold]{i}/{len(files)}[/bold]] [cyan]{path.name}[/cyan]")
        try:
            stem_dir = extract_stems(path, output_dir=out_dir, model=model, device=device)
            console.print(f"         [green]Stems saved →[/green] {stem_dir}\n")
        except Exception as exc:  # noqa: BLE001
            console.print(f"         [red]Failed:[/red] {exc}\n")

    console.print("[bold green]Done.[/bold green]\n")


# ---------------------------------------------------------------------------
# full
# ---------------------------------------------------------------------------

@app.command("full")
def full_cmd(
    folder: _FolderArg,
    mode: _ModeOpt = "both",
    model: Annotated[str, typer.Option("--stems-model", help="Demucs model")] = "4stems",
    device: Annotated[str, typer.Option("--device")] = "cpu",
    output: Annotated[Optional[Path], typer.Option("--output", "-o", help="Destination folder for tagged copies and stems")] = None,
    dry_run: _DryRunOpt = False,
) -> None:
    """Run full pipeline: BPM/key analysis + tag writing + stem extraction."""
    stems_out = (output / "stems") if output else None
    analyze_cmd(folder=folder, output=output, mode=mode, recursive=True, dry_run=dry_run)
    stems_cmd(folder=folder, output=stems_out, model=model, device=device, recursive=True)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _require_folder(folder: Path) -> None:
    if not folder.exists():
        console.print(f"[red]Error:[/red] Folder not found: {folder}")
        raise typer.Exit(1)
    if not folder.is_dir():
        console.print(f"[red]Error:[/red] Not a directory: {folder}")
        raise typer.Exit(1)


# Allow `python -m crate.cli`
if __name__ == "__main__":
    app()
