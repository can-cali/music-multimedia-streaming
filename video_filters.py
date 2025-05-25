"""
Video filter processing module for the MMS project.
This module provides a set of video filters using FFmpeg to process videos.
Each function takes input and output file paths and applies a specific filter.
"""
import subprocess
from pathlib import Path

def _ffmpeg(in_path: Path, vf: str, out_path: Path) -> None:
    """
    Internal helper function to execute FFmpeg commands.
    
    Args:
        in_path: Path to the input video file
        vf: FFmpeg video filter string 
        out_path: Path where the processed video will be saved
        
    Raises:
        RuntimeError: If FFmpeg command fails with an error
    """
    cmd = [
        "ffmpeg", "-y",
        "-i", str(in_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "fast",
        "-an",  # No audio
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
    """
    Converts the input video to grayscale.
    
    Args:
        in_path: Path to the input video file
        out_path: Path where the grayscale video will be saved
    """
    _ffmpeg(in_path, "format=gray", out_path)

def color_invert(in_path: Path, out_path: Path):
    """
    Inverts the colors in the input video (negative effect).
    
    Args:
        in_path: Path to the input video file
        out_path: Path where the color-inverted video will be saved
    """
    _ffmpeg(in_path, "negate", out_path)

def frame_interpolate(in_path: Path, out_path: Path, fps: int = 60):
    """
    Increases the frame rate of the video using motion interpolation.
    
    This function attempts to use the high quality 'minterpolate' filter first, 
    which generates new frames based on motion estimation. If that fails, it falls 
    back to the simpler 'fps' filter which duplicates frames.
    
    Args:
        in_path: Path to the input video file
        out_path: Path where the frame-interpolated video will be saved
        fps: Target frames per second (default: 60)
        
    Raises:
        FileNotFoundError: If the input file doesn't exist
    """
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
    """
    Upscales the video to a higher resolution using lanczos algorithm.
    
    Args:
        in_path: Path to the input video file
        out_path: Path where the upscaled video will be saved
        w: Target width in pixels (default: 1280)
        h: Target height in pixels (default: 720)
    """
    _ffmpeg(in_path, f"scale={w}:{h}:flags=lanczos", out_path)
