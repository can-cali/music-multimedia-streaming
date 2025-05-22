# filepath: c:\Users\Can\Documents\music\video_filter.py
import subprocess
from pathlib import Path

def _ffmpeg(in_path: Path, vf: str, out_path: Path) -> None:
    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-an",
        str(out_path),
    ]
    print(f"Running FFmpeg command: {' '.join(map(str, cmd))}")
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode:
        error_msg = proc.stderr.decode(errors="ignore")
        print(f"FFmpeg stderr ↓↓↓\n{error_msg}")
        raise RuntimeError(f"FFmpeg failed: {error_msg[:200]}...")

# ── effect wrappers ─────────────────────────────────────────────────────
def grayscale(in_path: Path, out_path: Path):
    _ffmpeg(in_path, "format=gray", out_path)

def color_invert(in_path: Path, out_path: Path):
    _ffmpeg(in_path, "negate", out_path)

def frame_interpolate(in_path: Path, out_path: Path, fps: int = 60):
    # Ensure the path exists and is readable
    if not in_path.exists():
        raise FileNotFoundError(f"Input file does not exist: {in_path}")
    
    # Use fps filter as a fallback which is more compatible
    try:
        # First try minterpolate which gives better quality
        _ffmpeg(in_path, f"minterpolate=fps={fps}:mi_mode=blend", out_path)
    except Exception as e:
        print(f"minterpolate failed: {str(e)}")
        print(f"Falling back to fps filter")
        # If minterpolate fails, try the simpler fps filter
        _ffmpeg(in_path, f"fps={fps}", out_path)

def upscale(in_path: Path, out_path: Path, w: int = 1280, h: int = 720):
    _ffmpeg(in_path, f"scale={w}:{h}:flags=lanczos", out_path)
