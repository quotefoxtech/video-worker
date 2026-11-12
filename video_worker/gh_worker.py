"""GitHub Actions render worker for the course-video pipeline.

Runs make_video.py on an Actions runner, streams per-step progress to
Cloudinary (p1.json, p2.json, ... — unique public_ids so the CDN never
serves stale progress), then uploads EVERY asset (video, images, audio,
script) to Cloudinary and finishes with result.json that the ReadyLMS
backend polls.

Usage:
    python gh_worker.py prepare --payload <base64-json>   # decode dispatch input
    python gh_worker.py run --cloud-name C --api-key K --api-secret S
    python gh_worker.py selftest                          # offline assertions
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).parent
WORKER_TIMEOUT_SEC = 60 * 45
UPLOAD_RETRIES = 3

# progress map inside the worker phase (LMS scales this into its 10-70% band)
WP_START, WP_TTS_BASE, WP_TTS_SPAN, WP_IMG_BASE, WP_IMG_SPAN, WP_RENDER_BASE = 0, 5, 35, 40, 30, 70


def _tlog(msg: str) -> None:
    print(f"\033[36m[worker] {msg}\033[0m", flush=True)


# ---------- cloudinary helpers ----------

def _cld_config(cloud_name: str, api_key: str, api_secret: str) -> None:
    import cloudinary
    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)


def _cld_upload(path: Path, public_id: str, resource_type: str) -> dict:
    """Upload with retries; returns the Cloudinary response dict."""
    import cloudinary.uploader
    last_err: Exception | None = None
    for attempt in range(1, UPLOAD_RETRIES + 1):
        try:
            res = cloudinary.uploader.upload(
                str(path), public_id=public_id, resource_type=resource_type,
                overwrite=False, invalidate=False)
            return res
        except Exception as e:  # noqa: BLE001 - retry transient upload failures
            last_err = e
            _tlog(f"upload attempt {attempt}/{UPLOAD_RETRIES} failed for {public_id}: {e}")
            time.sleep(3 * attempt)
    raise RuntimeError(f"cloudinary upload failed for {public_id}: {last_err}")


def push_progress(job_id: str, n: int, wp: int, message: str,
                  cloud: tuple[str, str, str]) -> str:
    """Upload p{n}.json — unique public_id per step, so delivery is never stale."""
    marker = ROOT / "topics" / f"_p_{job_id}_{n}.json"
    marker.write_text(json.dumps({"wp": int(wp), "message": message, "ts": time.time()}),
                      encoding="utf-8")
    try:
        res = _cld_upload(marker, f"readylms/gen/{job_id}/p{n}", "raw")
        return res["secure_url"]
    finally:
        marker.unlink(missing_ok=True)


# ---------- payload / parsing ----------

def decode_payload(payload_b64: str) -> dict:
    data = json.loads(base64.b64decode(payload_b64).decode("utf-8"))
    for key in ("job_id", "slug", "topic", "script"):
        if not data.get(key):
            raise ValueError(f"dispatch payload missing {key}")
    return data


def count_assets(log_text: str) -> tuple[int, int]:
    """Count completed TTS wavs and generated images from make_video output."""
    wavs = len(re.findall(r"(?:saved|cached)\s+\S+\.wav", log_text))
    imgs = len(re.findall(r"(?:\S+\.jpg\s+via\s+|cached\s+\S+\.jpg)", log_text))
    return wavs, imgs


def script_totals(slug: str) -> tuple[int, int]:
    """(tts_total, img_total) expected for this slug's script.json."""
    script = json.loads((ROOT / "topics" / slug / "script.json").read_text(encoding="utf-8"))
    scenes = [s for s in script.get("scenes", []) if isinstance(s, dict)]
    tts_total = sum(1 for s in scenes if (s.get("narration") or "").strip())
    img_total = sum(len(s.get("imagePrompts") or []) for s in scenes)
    return tts_total, img_total


def video_duration(slug: str) -> int:
    """Seconds of video, from props.json frame timings (30fps)."""
    props = ROOT / "topics" / slug / "props.json"
    if not props.exists():
        return 60
    try:
        timings = json.loads(props.read_text(encoding="utf-8")).get("timings", [])
        return int(sum(timings) / 30) if timings else 60
    except Exception:  # noqa: BLE001 - duration is cosmetic
        return 60


# ---------- commands ----------

def cmd_prepare(args) -> None:
    data = decode_payload(args.payload)
    slug = data["slug"]
    topic_dir = ROOT / "topics" / slug
    (topic_dir / "audio").mkdir(parents=True, exist_ok=True)
    (topic_dir / "images").mkdir(parents=True, exist_ok=True)
    (topic_dir / "script.json").write_text(
        json.dumps(data["script"], indent=2, ensure_ascii=False), encoding="utf-8")
    # single active job per runner — meta lives at topics/_job.json (run reads it there)
    (ROOT / "topics").mkdir(parents=True, exist_ok=True)
    (ROOT / "topics" / "_job.json").write_text(
        json.dumps({"job_id": data["job_id"], "slug": slug, "topic": data["topic"]}),
        encoding="utf-8")
    # make_video.py loads keys from its own .env (CAMB for TTS, FAL for images; proxies optional)
    lines = []
    if os.environ.get("CAMB_API_KEY"):
        lines.append(f"CAMB_API_KEY={os.environ['CAMB_API_KEY']}")
    if os.environ.get("CAMB_VOICE_ID"):
        lines.append(f"CAMB_VOICE_ID={os.environ['CAMB_VOICE_ID']}")
    if os.environ.get("CAMB_LANG"):
        lines.append(f"CAMB_LANG={os.environ['CAMB_LANG']}")
    if os.environ.get("FAL_KEY"):
        lines.append(f"FAL_KEY={os.environ['FAL_KEY']}")
    if os.environ.get("PROXY_LIST"):
        lines.append(f"PROXY_LIST={os.environ['PROXY_LIST']}")
    (ROOT / ".env").write_text("\n".join(lines) + "\n", encoding="utf-8")
    key_names = [ln.split("=")[0] for ln in lines] or ["NONE"]
    _tlog(f"pipeline .env written with keys: {', '.join(key_names)}"
          + ("" if "FAL_KEY" in key_names else "  ⚠ FAL_KEY missing — images will use the free chain"))
    _tlog(f"prepared '{slug}' ({len(data['script'].get('scenes', []))} scenes)")

def cmd_run(args) -> None:
    _cld_config(args.cloud_name, args.api_key, args.api_secret)
    _tlog(f"cloudinary cloud: {args.cloud_name}  <- isko secrets se match karo!")
    meta = json.loads((ROOT / "topics" / "_job.json").read_text(encoding="utf-8"))
    job_id, slug, topic = meta["job_id"], meta["slug"], meta["topic"]
    topic_dir = ROOT / "topics" / slug
    n = 0

    def push(wp: int, message: str) -> None:
        nonlocal n
        n += 1
        try:
            push_progress(job_id, n, wp, message, (args.cloud_name, args.api_key, args.api_secret))
            _tlog(f"progress p{n}: {wp}% — {message}")
        except Exception as e:  # noqa: BLE001 - a progress tick must never kill the run
            _tlog(f"progress upload failed (continuing): {e}")

    def finish(status: str, error: str | None = None, assets: dict | None = None) -> str:
        result_path = topic_dir / "_result.json"
        result_path.write_text(json.dumps(
            {"status": status, "error": error, "job_id": job_id, "slug": slug,
             "assets": assets or {}}, ensure_ascii=False), encoding="utf-8")
        res = _cld_upload(result_path, f"readylms/gen/{job_id}/result", "raw")
        result_path.unlink(missing_ok=True)
        return res["secure_url"]

    push(WP_START, "Render worker started")

    tts_total, img_total = script_totals(slug)
    log_lines: list[str] = []
    counters = {"tts": 0, "img": 0, "phase": "tts", "render_start": None}
    stop_creep = threading.Event()

    def creep() -> None:
        # render prints nothing for minutes — keep progress ticking (70-75)
        while not stop_creep.wait(60):
            elapsed = time.monotonic() - counters["render_start"] if counters["render_start"] else 0
            push(min(WP_RENDER_BASE + 5, WP_RENDER_BASE + elapsed / 60), "Rendering video…")

    proc = subprocess.Popen(
        [sys.executable, "-u", "make_video.py", "--topic", topic, "--reuse-script"],
        cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace", bufsize=1,
        env={**os.environ, "PYTHONUNBUFFERED": "1"})

    def on_line(line: str) -> None:
        log_lines.append(line)
        (topic_dir / "run.log").write_text("\n".join(log_lines[-800:]), encoding="utf-8")
        if "========" in line:
            if "2/4" in line:
                counters["phase"] = "tts"
            elif "3/4" in line:
                counters["phase"] = "images"
            elif "4/4" in line:
                counters["phase"] = "render"
                counters["render_start"] = time.monotonic()
                threading.Thread(target=creep, daemon=True).start()
                push(WP_RENDER_BASE, "Rendering video (longest step)…")
            return
        if (".wav" in line and ("saved" in line or "cached" in line)):
            counters["tts"] += 1
            wp = WP_TTS_BASE + WP_TTS_SPAN * min(1.0, counters["tts"] / max(1, tts_total))
            push(wp, f"Voiceover {counters['tts']}/{tts_total} scenes")
        elif re.search(r"\S+\.jpg\s+via\s+|cached\s+\S+\.jpg", line):
            counters["img"] += 1
            wp = WP_IMG_BASE + WP_IMG_SPAN * min(1.0, counters["img"] / max(1, img_total))
            push(wp, f"AI images {counters['img']}/{img_total}")

    def pump() -> None:
        for line in (proc.stdout or []):
            stripped = line.rstrip("\n")
            if stripped:
                _tlog(f"pipeline │ {stripped}")
            try:
                on_line(stripped)
            except Exception as e:  # noqa: BLE001 - parsing must never kill the run
                _tlog(f"line parse failed (continuing): {e}")

    watchdog = threading.Timer(WORKER_TIMEOUT_SEC, lambda: proc.kill())
    watchdog.start()
    try:
        pump()
        returncode = proc.wait()
    finally:
        stop_creep.set()
        watchdog.cancel()

    if returncode != 0 or not (topic_dir / "video.mp4").exists():
        tail = " | ".join(l.strip() for l in log_lines[-8:] if l.strip())
        url = finish("failed", error=f"render failed: {tail}")
        _tlog(f"FAILED — result: {url}")
        sys.exit(1)

    # upload every asset
    assets: dict = {}
    video_res = _cld_upload(topic_dir / "video.mp4", f"readylms/gen/{job_id}/video", "video")
    assets["video"] = {"url": video_res["secure_url"], "bytes": video_res.get("bytes", 0),
                       "public_id": video_res["public_id"]}
    assets["duration_sec"] = video_duration(slug)

    images, audio = [], []
    for img in sorted((topic_dir / "images").glob("*.jpg")):
        res = _cld_upload(img, f"readylms/gen/{job_id}/img/{img.stem}", "image")
        images.append({"name": img.name, "url": res["secure_url"],
                       "bytes": res.get("bytes", 0), "public_id": res["public_id"]})
    assets["images"] = images
    for wav in sorted((topic_dir / "audio").glob("*.wav")):
        res = _cld_upload(wav, f"readylms/gen/{job_id}/audio/{wav.stem}", "raw")
        audio.append({"name": wav.name, "url": res["secure_url"],
                      "bytes": res.get("bytes", 0), "public_id": res["public_id"]})
    assets["audio"] = audio

    script_res = _cld_upload(topic_dir / "script.json", f"readylms/gen/{job_id}/script", "raw")
    assets["script"] = {"url": script_res["secure_url"], "bytes": script_res.get("bytes", 0),
                        "public_id": script_res["public_id"]}

    push(100, "All assets uploaded to cloud storage")
    url = finish("completed", assets=assets)
    _tlog(f"DONE — result: {url}")


def cmd_selftest(args=None) -> None:
    payload = {"job_id": "a" * 24, "slug": "how-internet-works", "topic": "How internet works?",
               "script": {"topic": "How internet works?", "scenes": [{"id": "s1", "narration": "hi"}]}}
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    decoded = decode_payload(encoded)
    assert decoded["slug"] == "how-internet-works" and decoded["script"]["scenes"][0]["id"] == "s1"

    w, i = count_assets("  saved s1-abc.wav (12 KB)\n  cached s2-x.wav\n  s2-0.jpg via pollinations\ncached s3-1.jpg")
    assert (w, i) == (2, 2), (w, i)
    w2, i2 = count_assets("no matches here")
    assert (w2, i2) == (0, 0)
    assert script_totals.__doc__  # imported helpers exist
    print("selftest OK")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p_prepare = sub.add_parser("prepare")
    p_prepare.add_argument("--payload", required=True)
    p_run = sub.add_parser("run")
    p_run.add_argument("--cloud-name", required=True)
    p_run.add_argument("--api-key", required=True)
    p_run.add_argument("--api-secret", required=True)
    sub.add_parser("selftest")
    args = ap.parse_args()
    {"prepare": cmd_prepare, "run": cmd_run, "selftest": cmd_selftest}[args.cmd](args)


if __name__ == "__main__":
    main()
