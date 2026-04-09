"""
Write BPM and key metadata to audio files in formats understood by
Serato DJ Pro and Rekordbox.

Tag strategy:
  MP3 / AIFF  — ID3: TBPM (BPM) + TKEY (key)
  FLAC        — Vorbis comments: BPM + INITIALKEY
  M4A         — MP4 atoms: tmpo (BPM) + freeform initialkey

Serato reads TKEY as Camelot notation  (e.g. "8A").
Rekordbox reads TKEY as short notation (e.g. "Amin").
Mode "both" writes Camelot so both apps can read it — Rekordbox
also accepts Camelot since v6.
"""
import shutil
from pathlib import Path

from mutagen.aiff import AIFF
from mutagen.flac import FLAC
from mutagen.id3 import ID3, ID3NoHeaderError, TBPM, TKEY
from mutagen.mp4 import MP4

from .analyzer import AnalysisResult


def resolve_output_path(source: Path, source_root: Path, output_root: Path) -> Path:
    """
    Mirror the relative path of *source* under *output_root*.

    Example:
      source       = /music/house/track.mp3
      source_root  = /music
      output_root  = /tagged
      → returns    /tagged/house/track.mp3
    """
    relative = source.relative_to(source_root)
    dest = output_root / relative
    dest.parent.mkdir(parents=True, exist_ok=True)
    return dest


def write_tags(
    path: Path,
    result: AnalysisResult,
    mode: str = "both",
    output_root: Path | None = None,
    source_root: Path | None = None,
) -> Path:
    """
    Copy *path* to *output_root* (preserving subfolder structure) then tag the copy.
    If *output_root* is None the original file is tagged in place.

    Returns the path that was actually written to.

    mode:
      "serato"    — Camelot key  (e.g. "8A")
      "rekordbox" — Short key    (e.g. "Amin")
      "both"      — Camelot (readable by both apps since Rekordbox 6)
    """
    if output_root is not None:
        root = source_root or path.parent
        dest = resolve_output_path(path, root, output_root)
        shutil.copy2(path, dest)
        target = dest
    else:
        target = path

    key_value = result.rekordbox_key if mode == "rekordbox" else result.camelot
    suffix = target.suffix.lower()

    if suffix == ".mp3":
        _tag_mp3(target, result.bpm, key_value)
    elif suffix in (".aiff", ".aif"):
        _tag_aiff(target, result.bpm, key_value)
    elif suffix == ".flac":
        _tag_flac(target, result.bpm, key_value)
    elif suffix == ".m4a":
        _tag_m4a(target, result.bpm, key_value)
    else:
        _tag_mp3(target, result.bpm, key_value)

    return target


def _bpm_str(bpm: float) -> str:
    return str(int(round(bpm)))


def _tag_mp3(path: Path, bpm: float, key: str) -> None:
    try:
        tags = ID3(str(path))
    except ID3NoHeaderError:
        tags = ID3()

    tags.add(TBPM(encoding=3, text=[_bpm_str(bpm)]))
    tags.add(TKEY(encoding=3, text=[key]))
    tags.save(str(path))


def _tag_aiff(path: Path, bpm: float, key: str) -> None:
    audio = AIFF(str(path))
    if audio.tags is None:
        audio.add_tags()
    audio.tags.add(TBPM(encoding=3, text=[_bpm_str(bpm)]))
    audio.tags.add(TKEY(encoding=3, text=[key]))
    audio.save()


def _tag_flac(path: Path, bpm: float, key: str) -> None:
    audio = FLAC(str(path))
    audio["bpm"] = [_bpm_str(bpm)]
    audio["initialkey"] = [key]
    audio.save()


def _tag_m4a(path: Path, bpm: float, key: str) -> None:
    audio = MP4(str(path))
    audio["tmpo"] = [int(round(bpm))]
    # freeform atom — readable by both Serato and Rekordbox on M4A
    audio["----:com.apple.iTunes:initialkey"] = [key.encode()]
    audio.save()
