import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI()

# Clients call this from Obsidian's renderer via plain fetch() (see the
# QuickAdd script), which is subject to normal browser CORS rules. Wide open
# is fine here since the endpoint is already gated by AUTH_TOKEN below.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AUTH_TOKEN = os.environ.get("AUTH_TOKEN")

# Render "Secret Files" are mounted under /etc/secrets/<filename>. Export
# cookies.txt from a real, logged-in browser session (e.g. the "Get
# cookies.txt LOCALLY" extension) and add it there -- see README.md.
COOKIES_PATH = os.environ.get("YTDLP_COOKIES_PATH", "/etc/secrets/cookies.txt")


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
    return {"ok": True, "cookies_configured": os.path.exists(COOKIES_PATH)}


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
        ]
        if os.path.exists(COOKIES_PATH):
            cmd += ["--cookies", COOKIES_PATH]
        cmd += ["-o", out_template, req.url]

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
