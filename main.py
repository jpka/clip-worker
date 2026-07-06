import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI()

AUTH_TOKEN = os.environ.get("AUTH_TOKEN")


class ClipRequest(BaseModel):
    url: str
    start: str
    end: str


def check_auth(authorization: Optional[str]):
    if not AUTH_TOKEN:
        raise HTTPException(500, "Server misconfigured: AUTH_TOKEN not set")
    if authorization != f"Bearer {AUTH_TOKEN}":
        raise HTTPException(401, "Unauthorized")


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/clip")
def clip(req: ClipRequest, authorization: Optional[str] = Header(default=None)):
    check_auth(authorization)

    tmp_dir = tempfile.mkdtemp(prefix="clip_")
    try:
        out_template = str(Path(tmp_dir) / "clip.%(ext)s")
        cmd = [
            "yt-dlp",
            "--download-sections", f"*{req.start}-{req.end}",
            "--force-keyframes-at-cuts",
            "--remux-video", "mp4",
            "-o", out_template,
            req.url,
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode != 0:
            raise HTTPException(500, f"yt-dlp failed: {result.stderr[-2000:]}")

        files = list(Path(tmp_dir).glob("clip.*"))
        if not files:
            raise HTTPException(500, "yt-dlp produced no output file")

        data = files[0].read_bytes()
        return Response(content=data, media_type="video/mp4")
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Download timed out")
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
