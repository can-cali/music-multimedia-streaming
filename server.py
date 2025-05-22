
import subprocess, uuid, shutil
from pathlib import Path
from typing import List

import numpy as np
import soundfile as sf
import librosa

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

# ────────── local filters ──────────
import audio_filters as af          # music/audio_filters.py
import video_filter as vf          # music/video_filters.py

# ────────── paths ──────────
BASE_DIR   = Path(__file__).parent.resolve()      # …/music/
STATIC_DIR = BASE_DIR / "static"           # …/static/
MEDIA_DIR  = STATIC_DIR / "media"
UPLOAD_DIR = MEDIA_DIR / "uploads"
PROC_DIR   = MEDIA_DIR / "processed"
for d in (UPLOAD_DIR, PROC_DIR):
    d.mkdir(parents=True, exist_ok=True)

# ────────── fastapi app ──────────
app = FastAPI(title="Project MMS")

# ────────── in-memory state ──────────
state: dict[str, Path | list | None] = {
    "uploaded":  None,   # Path of original video
    "processed": None,   # Path of filtered video
    "filters":   None,   # List[FilterCfg]
}

# ────────── schema ──────────
class Prop(BaseModel):
    name: str
    value: str | float | int

class FilterCfg(BaseModel):
    name : str                 # e.g.  grayscale / gainCompressor
    props: List[Prop] = []     # list of (name,value) pairs

class FilterList(BaseModel):
    filters: List[FilterCfg]

# ────────── helpers ──────────
def _cleanup() -> None:
    "Remove stored files and reset the state dict."
    for k in ("uploaded", "processed"):
        p: Path | None = state[k]              # type: ignore
        if p and p.exists():
            p.unlink()
    state.update(uploaded=None, processed=None, filters=None)

def _ffmpeg(*args: str | Path) -> None:
    "Run ffmpeg; raise if it fails."
    cmd = ["ffmpeg", "-y", *map(str, args)]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode:
        raise RuntimeError(proc.stderr.decode()[:400])

# maps—string from HTML  →  wrapper function
VIDEO_MAP = {
    "grayscale"       : vf.grayscale,
    "colorinvert"     : vf.color_invert,
    "frameInterpolate": lambda i, o, **k: vf.frame_interpolate(
        i, o, int(k.get("frameInterpolateTargetFps", 60))
    ),
    "upscale": lambda i,o,**k: vf.upscale(
        i, o,
        int(k.get("upscaleTargetWidth", 1280)),
        int(k.get("upscaleTargetHeight", 720)),
    ),
}
AUDIO_MAP = {
    "gainCompressor" : lambda x,sr,**k: af.gain_compress(
                        x, float(k.get("gainCompressorThreshold",-1)),
                           float(k.get("limiterThreshold",0))),
    "voiceEnhancement": lambda x,sr,**k: af.voice_enhancement(
                        x, sr, float(k.get("preemphasisAlpha",0.3)),
                              int(k.get("highPassFilter",2))),
    "denoiseDelay"   : lambda x,sr,**k: af.denoise_delay(
                        x, sr, float(k.get("noisePower",-15)),
                              int(k.get("delay",100)),
                          float(k.get("delayGain",50))),
    "phone"          : lambda x,sr,**k: af.phone_filter(
                        x, sr, float(k.get("phoneSideGain",0)),
                              int(k.get("phoneFilterOrder",1))),
    "car"            : lambda x,sr,**k: af.car_filter(
                        x, sr, float(k.get("carSideGain",3)),
                              int(k.get("carFilterOrder",1))),
}

# ────────── endpoints ──────────
@app.post("/upload")
async def upload_video(file: UploadFile = File(...)):
    if state["uploaded"]:
        raise HTTPException(409, "Video already uploaded – delete first")
    dest = UPLOAD_DIR / f"{uuid.uuid4()}.mp4"
    with dest.open("wb") as fh:
        shutil.copyfileobj(file.file, fh)
    state["uploaded"] = dest
    return {"file": dest.name}

@app.delete("/upload")
async def delete_video():
    if not state["uploaded"]:
        raise HTTPException(404, "Nothing to delete")
    _cleanup()
    return {"ok": True}

@app.post("/filters")
async def configure_filters(fl: FilterList):
    # basic validation
    for f in fl.filters:
        if f.name not in VIDEO_MAP and f.name not in AUDIO_MAP:
            raise HTTPException(400, f"Unknown filter {f.name}")
    state["filters"] = fl.filters
    return {"count": len(fl.filters)}

@app.post("/apply")
async def apply_filters():
    src: Path | None = state["uploaded"]
    if not src:
        raise HTTPException(400, "No video uploaded")
    if not state["filters"]:
        raise HTTPException(400, "No filters configured")

    # split filters
    audio_cfgs = [f for f in state["filters"] if f.name in AUDIO_MAP]
    video_cfgs = [f for f in state["filters"] if f.name in VIDEO_MAP]    # ── video chain ──────────────────────────────────────
    cur_vid = src
    for idx, f in enumerate(video_cfgs):
        tmp = PROC_DIR / f"vidstep_{idx}.mp4"
        print(f"Applying video filter: {f.name} with props: {f.props}")
        try:
            VIDEO_MAP[f.name](cur_vid, tmp, **{p.name: p.value for p in f.props})
            cur_vid = tmp
        except Exception as e:
            print(f"Error applying {f.name} filter: {str(e)}")
            raise    # ── audio chain ──────────────────────────────────────
    wav_orig = PROC_DIR / "audio_orig.wav"
    _ffmpeg("-i", src, "-vn", wav_orig)
    y, sr = librosa.load(wav_orig, sr=None, mono=False)
    for f in audio_cfgs:
        print(f"Applying audio filter: {f.name} with props: {f.props}")
        try:
            y = AUDIO_MAP[f.name](y, sr, **{p.name: p.value for p in f.props})
        except Exception as e:
            print(f"Error applying audio {f.name} filter: {str(e)}")
            raise
    wav_proc = PROC_DIR / "audio_proc.wav"
    sf.write(wav_proc, y.T if y.ndim > 1 else y, sr)

    # ── mux video+audio ──────────────────────────────────
    out = PROC_DIR / f"processed_{uuid.uuid4()}.mp4"
    _ffmpeg("-i", cur_vid, "-i", wav_proc, "-c:v", "copy", "-c:a", "aac", out)

    state["processed"] = out
    # clean stage files
    for p in PROC_DIR.glob("vidstep_*.mp4"): p.unlink()
    wav_orig.unlink(missing_ok=True); wav_proc.unlink(missing_ok=True)

    return {"file": out.name}

@app.get("/stream")
async def stream():
    p: Path | None = state["processed"]
    if not p or not p.exists():
        raise HTTPException(404, "Nothing to stream – apply filters first")
    return StreamingResponse(p.open("rb"), media_type="video/mp4")

# ────────── SPA entry-point & static files ──────────
@app.get("/")
async def root():
    return FileResponse(STATIC_DIR / "index.html")

# serve all other static assets (CSS, imgs…) under /static/*
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
