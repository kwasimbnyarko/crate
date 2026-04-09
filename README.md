# Crate

DJ-ready audio analysis for Serato DJ Pro and Rekordbox. Scans a folder of audio files, detects BPM and musical key, writes the results as ID3/Vorbis/MP4 tags, and separates tracks into stems.

## Features

- **BPM detection** via librosa beat tracking
- **Key detection** via Krumhansl-Schmuckler chroma analysis, with Camelot wheel notation
- **Tag writing** in formats read by Serato DJ Pro and Rekordbox (MP3, FLAC, AIFF, M4A, WAV)
- **Stem separation** into vocals, drums, bass, and other via Meta's Demucs
- **Non-destructive** — copy files to a separate output folder before tagging, originals untouched
- **GUI** and **CLI** interfaces

## Compatibility

| | Serato DJ Pro | Rekordbox |
|---|---|---|
| Key tag | Reads on import, skips re-analysis | Reads on import |
| BPM tag | Reads on import, skips re-analysis | Ignores — always re-analyses |
| Stems | Not supported (uses built-in real-time separation) | Not supported (uses built-in real-time separation) |

## Installation

Requires Python 3.10+ and [ffmpeg](https://ffmpeg.org/download.html).

```bash
# macOS
brew install ffmpeg python-tk@3.13

git clone https://github.com/kwasimbnyarko/crate
cd crate
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

## Usage

### GUI

```bash
crate-gui
```

Pick a **Source** folder, optionally pick an **Output** folder (tagged copies go there — originals untouched), choose your options and hit a pipeline button.

| Button | What it does |
|---|---|
| Analyse (BPM + Key) | Detects BPM and key, writes tags |
| Extract Stems | Separates each track into stems via Demucs |
| Full Pipeline | Both of the above |

### CLI

```bash
# Analyse and tag in place
crate analyze /path/to/music

# Copy to a separate folder, tag the copies
crate analyze /path/to/music --output /path/to/tagged

# Extract stems (saved to /path/to/music/stems by default)
crate stems /path/to/music

# Full pipeline — tagged copies and stems all under one output folder
crate full /path/to/music --output /path/to/output

# Dry run — analyse only, no files written
crate analyze /path/to/music --dry-run
```

#### Options

| Flag | Default | Description |
|---|---|---|
| `--output / -o` | *(none — in place)* | Destination folder for tagged copies |
| `--mode / -m` | `both` | Tag format: `serato`, `rekordbox`, or `both` |
| `--device` | `cpu` | Inference device for Demucs: `cpu`, `mps` (Apple Silicon), `cuda` (NVIDIA) |
| `--stems-model` | `4stems` | Demucs model: `4stems`, `4stems-ft`, `6stems` |
| `--recursive / -r` | `True` | Scan subfolders |
| `--dry-run` | `False` | Analyse without writing any files |

### Stems models

| Model | Stems | Notes |
|---|---|---|
| `4stems` | vocals, drums, bass, other | Default, best speed/quality balance |
| `4stems-ft` | vocals, drums, bass, other | Fine-tuned per stem, slightly better quality |
| `6stems` | vocals, drums, bass, guitar, piano, other | Most detailed separation |

### GPU acceleration

Stem separation is CPU-bound by default and slow on large libraries. Pass `--device mps` on Apple Silicon or `--device cuda` on NVIDIA for significantly faster runs.

## Output structure

When an output folder is specified, the source folder's subfolder structure is mirrored:

```
source/
  house/
    track.mp3
  techno/
    track2.flac

output/
  house/
    track.mp3       ← tagged copy
  techno/
    track2.flac     ← tagged copy
  stems/
    htdemucs/
      track/
        vocals.wav
        drums.wav
        bass.wav
        other.wav
```
