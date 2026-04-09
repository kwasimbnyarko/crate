from pathlib import Path

AUDIO_EXTENSIONS = {".mp3", ".wav", ".flac", ".aiff", ".aif", ".m4a", ".ogg", ".opus"}


def scan_folder(folder: Path, recursive: bool = True) -> list[Path]:
    """Return sorted list of audio files found in folder."""
    files: list[Path] = []

    if recursive:
        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                files.append(path)
    else:
        for path in folder.iterdir():
            if path.is_file() and path.suffix.lower() in AUDIO_EXTENSIONS:
                files.append(path)

    return sorted(files)
