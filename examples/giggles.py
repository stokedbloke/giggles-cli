#!/usr/bin/env python3
"""
giggles 0.5.0 — YAMNet(TFLite) laughter detector + optional Limitless pull

What this does:
  1) (Optional) Pull pendant audio (.ogg, Ogg Opus) from Limitless for a time window.
     - Official base: https://api.limitless.ai
     - Endpoint:      GET /v1/download-audio?startMs=...&endMs=...
     - Auth:          X-API-Key: <your key>
     - Max span per request: 2 hours (7,200,000 ms)

  2) Decode each .ogg to mono 16 kHz float32 via ffmpeg and run YAMNet (TFLite).
     - Input to YAMNet TFLite MUST be a 1-D float32 waveform at 16 kHz.
       (Passing rank-2/3 arrays is exactly what triggers the pad/dimension errors.)

  3) Write JSONL of laughter segments with file timestamps.

API key sources (checked in this order):
  - env: LIMITLESS_API_KEY
  - macOS Keychain item named: LIMITLESS_API_KEY  (via `security` CLI)

Notes:
  - You do NOT need to provide a “base URL” anymore. We pin it to https://api.limitless.ai.
  - You can run with --pull to fetch audio into --downloads-dir (skips files that already exist).
  - If you already have .ogg files, you can skip --pull and just point --input-dir to them.
  - YAMNet TFLite file expected at: ./models/yamnet.tflite  (contains "TFL3" in first 32 bytes)
  - Optional labels at: ./models/labels.txt, otherwise we assume "laughter" is class index 13.

Usage example:
  python3 giggles.py \
    --tz America/Los_Angeles \
    --start 2025-09-29 --end 2025-10-08 \
    --downloads-dir ./downloads \
    --input-dir ./downloads \
    --out ./out/laughter.jsonl \
    --pull \
    --min-prob 0.35 \
    --max-workers 4
"""
from __future__ import annotations

import argparse
import concurrent.futures as cf
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple

# ---- Constants -------------------------------------------------------------

APP_VERSION = "0.5.0"
API_BASE = "https://api.limitless.ai"
DL_PATH = "/v1/download-audio"
MAX_SPAN_MS = 7_200_000  # 2 hours per official docs

# YAMNet timing (from the official model):
PATCH_WINDOW_SEC = 0.96
PATCH_HOP_SEC = 0.48

# ---------------------------------------------------------------------------

def log(*msg):
    print(*msg, file=sys.stderr)

def die(*msg, code: int = 1):
    log(*msg)
    sys.exit(code)

# ---- Keychain / API Key ----------------------------------------------------

def read_api_key_from_keychain(service_name: str = "LIMITLESS_API_KEY") -> Optional[str]:
    """macOS-only: read secret from Keychain using the 'security' CLI."""
    try:
        out = subprocess.check_output(
            ["security", "find-generic-password", "-w", "-s", service_name],
            stderr=subprocess.DEVNULL,
        )
        key = out.decode("utf-8").strip()
        return key if key else None
    except Exception:
        return None

def get_api_key() -> Optional[str]:
    k = os.getenv("LIMITLESS_API_KEY")
    if k:
        return k.strip()
    return read_api_key_from_keychain("LIMITLESS_API_KEY")

# ---- Time helpers ----------------------------------------------------------

def parse_zoneinfo(name: str):
    try:
        from zoneinfo import ZoneInfo
        return ZoneInfo(name)
    except Exception:
        log(f"WARNING: zoneinfo unavailable; using UTC for {name}")
        return timezone.utc

def parse_local_iso(s: str, tz_name: str) -> datetime:
    tz = parse_zoneinfo(tz_name)
    if len(s) == 10:
        # YYYY-MM-DD only
        dt_local = datetime.strptime(s, "%Y-%m-%d").replace(tzinfo=tz)
    else:
        # ISO, maybe with offset
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt_local = dt.replace(tzinfo=tz)
        else:
            dt_local = dt.astimezone(tz)
    return dt_local.astimezone(timezone.utc)

def to_ms(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp() * 1000)

def chunk_range(start_ms: int, end_ms: int, max_span_ms: int = MAX_SPAN_MS):
    cur = start_ms
    while cur < end_ms:
        nxt = min(cur + max_span_ms, end_ms)
        yield cur, nxt
        cur = nxt

def chunk_name_utc(start_ms: int, end_ms: int) -> str:
    s = datetime.utcfromtimestamp(start_ms / 1000).strftime("%Y%m%d_%H%M%S")
    e = datetime.utcfromtimestamp(end_ms / 1000).strftime("%Y%m%d_%H%M%S")
    return f"{s}-{e}.ogg"

# ---- HTTP download (urllib) ------------------------------------------------

def http_get_binary(url: str, headers: dict, timeout: int = 120) -> bytes:
    import urllib.request
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        if resp.status != 200:
            raise RuntimeError(f"HTTP {resp.status}")
        return resp.read()

def pull_audio_window(api_key: str, tz: str, start: str, end: str, out_dir: Path) -> int:
    start_utc = parse_local_iso(start, tz)
    end_utc = parse_local_iso(end, tz)
    if end_utc <= start_utc:
        die("ERROR: end must be after start")

    out_dir.mkdir(parents=True, exist_ok=True)
    total = 0
    for s_ms, e_ms in chunk_range(to_ms(start_utc), to_ms(end_utc)):
        name = chunk_name_utc(s_ms, e_ms)
        dest = out_dir / name
        if dest.exists():
            log(f"skip  {name} (already exists)")
            continue

        url = f"{API_BASE}{DL_PATH}?startMs={s_ms}&endMs={e_ms}"
        headers = {"X-API-Key": api_key}
        log(f"pull  {name}")
        try:
            data = http_get_binary(url, headers=headers, timeout=300)
            # light magic: Ogg files typically start with "OggS"
            if not data.startswith(b"OggS"):
                log(f"WARNING: {name} does not start with 'OggS' (size={len(data)} bytes). Saving anyway.")
            dest.write_bytes(data)
            total += 1
        except Exception as e:
            log(f"ERROR downloading {name}: {e}")
            if dest.exists():
                dest.unlink(missing_ok=True)

    return total

# ---- FFmpeg discovery & decode --------------------------------------------

def find_ffmpeg() -> Optional[str]:
    # Honor explicit env override
    env_bin = os.getenv("FFMPEG_BINARY")
    if env_bin and Path(env_bin).exists():
        return env_bin
    # System PATH
    p = shutil.which("ffmpeg")
    if p:
        return p
    # imageio-ffmpeg bundled binary as a last resort
    try:
        import imageio_ffmpeg as ioff
        return ioff.get_ffmpeg_exe()
    except Exception:
        return None

def decode_audio_ffmpeg(ffmpeg_bin: str, src_path: Path) -> "np.ndarray":
    """
    Decode src_path to mono 16kHz float32 PCM using ffmpeg, stream to stdout,
    and return as a NumPy 1-D float32 array.

    IMPORTANT: YAMNet TFLite wants a 1-D float32 waveform at 16kHz.
    """
    import numpy as np

    cmd = [
        ffmpeg_bin,
        "-hide_banner", "-loglevel", "error",
        "-i", str(src_path),
        "-ac", "1",
        "-ar", "16000",
        "-f", "f32le",
        "pipe:1",
    ]
    try:
        raw = subprocess.check_output(cmd)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"ffmpeg decode failed: {e}")

    # bytes -> float32 array
    arr = np.frombuffer(raw, dtype="<f4")  # little-endian float32
    return arr

# ---- YAMNet (TFLite) -------------------------------------------------------

@dataclass
class YamnetModel:
    interpreter: "tf.lite.Interpreter"
    input_index: int
    output_index: int
    labels: List[str]
    laugh_index: int

    @staticmethod
    def load(model_path: Path, labels_path: Optional[Path]) -> "YamnetModel":
        import numpy as np
        import tensorflow as tf

        # Basic validation: we just need to ensure it's a TFLite file (contains TFL3 near the header).
        header = model_path.read_bytes()[:32]
        if b"TFL3" not in header:
            die(f"ERROR: {model_path} does not look like a TFLite (missing 'TFL3' in first 32 bytes).")

        interpreter = tf.lite.Interpreter(model_path=str(model_path), num_threads=max(1, os.cpu_count() or 1))
        interpreter.allocate_tensors()

        input_details = interpreter.get_input_details()
        output_details = interpreter.get_output_details()

        if not input_details:
            die("ERROR: TFLite model reports no input tensors.")
        if not output_details:
            die("ERROR: TFLite model reports no output tensors.")

        input_index = input_details[0]["index"]
        output_index = output_details[0]["index"]

        # labels
        labels: List[str] = []
        laugh_index = 13  # fallback; in YAMNet it's typically 13 in 521-class map
        if labels_path and labels_path.exists():
            with labels_path.open("r", encoding="utf-8") as f:
                labels = [ln.strip() for ln in f if ln.strip()]
            # Try to locate 'laughter'
            for i, lab in enumerate(labels):
                if lab.lower() == "laughter":
                    laugh_index = i
                    break

        return YamnetModel(interpreter, input_index, output_index, labels, laugh_index)

    def infer(self, waveform_16k_f32_1d: "np.ndarray") -> "np.ndarray":
        """
        Give YAMNet a 1-D float32 waveform @16kHz. The model handles framing inside.
        Returns scores of shape [num_patches, num_classes].
        """
        import numpy as np
        x = waveform_16k_f32_1d.astype(np.float32, copy=False)

        # IMPORTANT: set a *1-D* tensor. Passing rank-2/3 triggers the PAD errors you saw.
        self.interpreter.resize_tensor_input(self.input_index, [x.shape[0]], strict=True)
        self.interpreter.allocate_tensors()
        self.interpreter.set_tensor(self.input_index, x)
        try:
            self.interpreter.invoke()
        except Exception as e:
            raise RuntimeError(f"TFLite invoke failed: {e}")

        scores = self.interpreter.get_tensor(self.output_index)
        return scores  # [num_patches, num_classes]

# ---- Laughter segmentation -------------------------------------------------

def scores_to_segments(
    scores: "np.ndarray",
    laugh_idx: int,
    min_prob: float
) -> List[Tuple[float, float, float]]:
    """
    Convert per-patch scores into [ (start_sec, end_sec, prob), ... ] for patches
    where 'laughter' probability >= min_prob. Each patch covers 0.96 s and hops by 0.48 s.
    """
    import numpy as np
    if scores.ndim != 2:
        return []

    if laugh_idx < 0 or laugh_idx >= scores.shape[1]:
        return []

    probs = scores[:, laugh_idx]
    segs: List[Tuple[float, float, float]] = []
    for i, p in enumerate(probs):
        if p >= min_prob:
            start = i * PATCH_HOP_SEC
            end = start + PATCH_WINDOW_SEC
            segs.append((start, end, float(p)))
    return segs

# ---- File discovery --------------------------------------------------------

def list_audio_files(input_dir: Path) -> List[Path]:
    # We only process .ogg by default (what Limitless endpoint returns)
    return sorted(input_dir.glob("*.ogg"))

# ---- JSONL writer ----------------------------------------------------------

def write_jsonl(out_path: Path, rows: List[dict]):
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

# ---- Main ------------------------------------------------------------------

def main():
    print(f"giggles {APP_VERSION} (yamnet-puller-stable)")
    # Lazy import heavy deps to minimize startup noise
    try:
        import tensorflow as tf  # noqa: F401
    except Exception:
        die("ERROR: TensorFlow is required (for TFLite). Try: pip install 'tensorflow==2.13.1'")

    p = argparse.ArgumentParser(description="Detect laughter in Limitless pendant audio using YAMNet (TFLite).")
    p.add_argument("--tz", default="UTC", help="IANA timezone for interpreting --start/--end (default UTC)")
    p.add_argument("--start", help="Start (e.g. 2025-09-29 or 2025-09-29T00:00:00)")
    p.add_argument("--end", help="End   (e.g. 2025-10-08 or 2025-10-08T00:00:00)")
    p.add_argument("--downloads-dir", default="./downloads", help="Where to save pulled .ogg files")
    p.add_argument("--input-dir", default="./downloads", help="Where to read .ogg files for analysis")
    p.add_argument("--out", required=True, help="Output JSONL path (e.g., ./out/laughter.jsonl)")
    p.add_argument("--pull", action="store_true", help="Pull audio from Limitless before processing")
    p.add_argument("--min-prob", type=float, default=0.50, help="Minimum probability to keep a laughter patch")
    p.add_argument("--max-workers", type=int, default=2, help="Parallel decode/infer workers")
    p.add_argument("--yamnet", default="./models/yamnet.tflite", help="Path to YAMNet TFLite file")
    p.add_argument("--labels", default="./models/labels.txt", help="Optional labels file (to locate 'laughter')")
    args = p.parse_args()

    # Show environment
    py = sys.executable
    ffbin = find_ffmpeg()
    print(f"Python: {py}")
    try:
        import tensorflow as tf
        print(f"TensorFlow: {tf.__version__}")
    except Exception:
        print("TensorFlow: (import error)")
    print(f"FFmpeg: {ffbin or 'NOT FOUND'}")

    if not ffbin:
        die("ERROR: ffmpeg not found. Install it or set FFMPEG_BINARY to a valid path.")

    # Pull (optional)
    if args.pull:
        if not args.start or not args.end:
            die("ERROR: --pull requires --start and --end.")
        api_key = get_api_key()
        if not api_key:
            die("ERROR: --pull requested but no LIMITLESS_API_KEY (env or macOS Keychain item) found.")
        dl_dir = Path(args.downloads_dir).expanduser().resolve()
        new_files = pull_audio_window(api_key, args.tz, args.start, args.end, dl_dir)
        print(f"Pulled {new_files} new file(s) into {dl_dir}")

    # Load model (strict but clear validation)
    yam_path = Path(args.yamnet).expanduser().resolve()
    if not yam_path.exists():
        die(f"ERROR: YAMNet TFLite not found at {yam_path}")
    header = yam_path.read_bytes()[:32]
    if b"TFL3" not in header:
        die(f"ERROR: {yam_path} does not look like TFLite (no 'TFL3' in first 32 bytes).")

    labels_path = Path(args.labels).expanduser().resolve()
    ymod = YamnetModel.load(yam_path, labels_path if labels_path.exists() else None)
    if ymod.labels:
        print(f"Loaded {len(ymod.labels)} labels; using 'laughter' index: {ymod.laugh_index}")
    else:
        print(f"No labels file found; defaulting 'laughter' index: {ymod.laugh_index}")

    # Discover audio files
    in_dir = Path(args.input_dir).expanduser().resolve()
    files = list_audio_files(in_dir)
    if not files:
        die(f"No .ogg files found in {in_dir}. Use --pull or put files there.")

    # Process files (parallel)
    rows: List[dict] = []
    def process_one(path: Path) -> List[dict]:
        import numpy as np
        rel = str(path.relative_to(in_dir)) if path.is_file() else path.name
        try:
            wav = decode_audio_ffmpeg(ffbin, path)  # 1-D float32 @ 16kHz
            # Short-circuit: ignore totally empty decodes
            if wav.size == 0:
                log(f"WARNING: Empty decode: {rel}")
                return []
            scores = ymod.infer(wav)  # [num_patches, num_classes]
            segs = scores_to_segments(scores, ymod.laugh_index, args.min_prob)
            out = []
            for (s, e, p) in segs:
                out.append({
                    "file": rel,
                    "start_sec": round(float(s), 3),
                    "end_sec": round(float(e), 3),
                    "prob": round(float(p), 4),
                })
            return out
        except Exception as e:
            log(f"[{rel}] ERROR: {e}")
            return []

    with cf.ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as ex:
        for chunk in ex.map(process_one, files):
            rows.extend(chunk)

    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    write_jsonl(out_path, rows)
    print(f"Done. Wrote {out_path} ({len(rows)} rows)")

if __name__ == "__main__":
    main()
