"""
Stem separation using Meta's Demucs.

Models:
  htdemucs    — 4 stems: vocals, drums, bass, other  (default, best quality)
  htdemucs_ft — 4 stems, fine-tuned per-stem (slightly better, slower)
  htdemucs_6s — 6 stems: vocals, drums, bass, guitar, piano, other

GPU acceleration:
  Pass device="cuda" (NVIDIA) or device="mps" (Apple Silicon) for faster runs.
  Defaults to "cpu" which works on any machine.
"""
import subprocess
import sys
from pathlib import Path


MODELS = {
    "4stems": "htdemucs",
    "4stems-ft": "htdemucs_ft",
    "6stems": "htdemucs_6s",
}


def extract_stems(
    path: Path,
    output_dir: Path | None = None,
    model: str = "4stems",
    device: str = "cpu",
) -> Path:
    """
    Run Demucs on *path* and return the directory containing the separated stems.

    Stems are written to:
      output_dir / <model_name> / <track_stem> / {vocals,drums,bass,...}.wav
    """
    if output_dir is None:
        output_dir = path.parent / "stems"

    output_dir.mkdir(parents=True, exist_ok=True)

    model_name = MODELS.get(model, model)  # allow passing model name directly

    cmd = [
        sys.executable, "-m", "demucs",
        "--name", model_name,
        "--out", str(output_dir),
        "--device", device,
        str(path),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True)

    if proc.returncode != 0:
        raise RuntimeError(
            f"demucs failed for '{path.name}':\n{proc.stderr.strip()}"
        )

    stem_dir = output_dir / model_name / path.stem
    return stem_dir
