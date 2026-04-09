from dataclasses import dataclass
from pathlib import Path

import librosa
import numpy as np


# Krumhansl-Schmuckler key profiles
_MAJOR_PROFILE = np.array([6.35, 2.23, 3.48, 2.33, 4.38, 4.09, 2.52, 5.19, 2.39, 3.66, 2.29, 2.88])
_MINOR_PROFILE = np.array([6.33, 2.68, 3.52, 5.38, 2.60, 3.53, 2.54, 4.75, 3.98, 2.69, 3.34, 3.17])

_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]

# Camelot wheel mapping (used by Serato DJ Pro)
CAMELOT: dict[str, str] = {
    "C major": "8B",  "G major": "9B",  "D major": "10B", "A major": "11B",
    "E major": "12B", "B major": "1B",  "F# major": "2B", "C# major": "3B",
    "G# major": "4B", "D# major": "5B", "A# major": "6B", "F major": "7B",
    "A minor": "8A",  "E minor": "9A",  "B minor": "10A", "F# minor": "11A",
    "C# minor": "12A","G# minor": "1A", "D# minor": "2A", "A# minor": "3A",
    "F minor": "4A",  "C minor": "5A",  "G minor": "6A",  "D minor": "7A",
}

# Rekordbox uses short notation e.g. "Amaj" / "Amin"
REKORDBOX_KEY: dict[str, str] = {
    "C major": "Cmaj",   "G major": "Gmaj",   "D major": "Dmaj",   "A major": "Amaj",
    "E major": "Emaj",   "B major": "Bmaj",   "F# major": "F#maj", "C# major": "C#maj",
    "G# major": "G#maj", "D# major": "D#maj", "A# major": "A#maj", "F major": "Fmaj",
    "A minor": "Amin",   "E minor": "Emin",   "B minor": "Bmin",   "F# minor": "F#min",
    "C# minor": "C#min", "G# minor": "G#min", "D# minor": "D#min", "A# minor": "A#min",
    "F minor": "Fmin",   "C minor": "Cmin",   "G minor": "Gmin",   "D minor": "Dmin",
}


@dataclass
class AnalysisResult:
    bpm: float
    key: str        # e.g. "A minor"
    camelot: str    # e.g. "8A"
    rekordbox_key: str  # e.g. "Amin"
    confidence: float


def _detect_key(y: np.ndarray, sr: int) -> tuple[str, float]:
    """Krumhansl-Schmuckler algorithm over chroma features."""
    chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
    chroma_mean = chroma.mean(axis=1)

    best_key = "C major"
    best_corr = -np.inf

    for i, note in enumerate(_NOTES):
        corr_major = float(np.corrcoef(chroma_mean, np.roll(_MAJOR_PROFILE, i))[0, 1])
        if corr_major > best_corr:
            best_corr = corr_major
            best_key = f"{note} major"

        corr_minor = float(np.corrcoef(chroma_mean, np.roll(_MINOR_PROFILE, i))[0, 1])
        if corr_minor > best_corr:
            best_corr = corr_minor
            best_key = f"{note} minor"

    return best_key, best_corr


def analyze(path: Path) -> AnalysisResult:
    """Analyze a single audio file and return BPM, key, and Camelot notation."""
    y, sr = librosa.load(str(path), sr=None, mono=True)

    # BPM — np.atleast_1d handles both scalar and array returns across librosa versions
    tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
    bpm = round(float(np.atleast_1d(tempo)[0]), 2)

    key, confidence = _detect_key(y, sr)

    return AnalysisResult(
        bpm=bpm,
        key=key,
        camelot=CAMELOT.get(key, "?"),
        rekordbox_key=REKORDBOX_KEY.get(key, key),
        confidence=round(confidence, 4),
    )
