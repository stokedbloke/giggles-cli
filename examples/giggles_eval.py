#!/usr/bin/env python3
"""
giggles_eval.py — ultra-MVP for human eval of laughter segments.

Inputs
------
1) --segments-jsonl  Path to JSONL produced earlier (one JSON object per line),
   shaped like either of these minimal forms:
   A) Per-file object with a "file" and "segments" list:
      {"file": ".../2025-09-30T21-46-57__2025-09-30T23-51-49.ogg",
       "segments": [{"start": 1599.84, "end": 1600.8, "avg_prob": 0.32}, ...]}

   B) Flat objects (one per segment):
      {"file": ".../xxx.ogg", "start": 12.34, "end": 13.02, "avg_prob": 0.78}

2) --input-audio-dir  Folder that contains your .ogg/.wav files (optional; paths
   in JSONL can be absolute; this dir is used to resolve relative file names).

What it produces
----------------
• A snippets/ folder with per-segment audio clips (wav by default).
• A JSONL tracelog: out/trace.jsonl — one object per kept segment:
  {
    "id": "...",
    "file": "/abs/path/original.ogg",
    "start": 12.3,
    "end": 14.9,
    "avg_prob": 0.82,
    "snippet": "out/snippets/file__00023.wav",
    "comment": ""
  }

• A static HTML report: out/report.html — play buttons, probability, and a
  comment box. A small JS lets you export your annotations as a new JSONL file,
  no server required.

No TensorFlow, no NumPy, no STT. Just Python stdlib + ffmpeg.

Dependencies
------------
- ffmpeg must be runnable. The script looks for it in this order:
  1) env FFMPEG_BINARY
  2) PATH (shutil.which("ffmpeg"))
  3) imageio_ffmpeg (optional): uses its bundled binary if installed
If none is found, snippets are skipped, but the report still renders (it’ll point
at non-existent audio files).

Usage
-----
python giggles_eval.py \
  --segments-jsonl ~/Documents/GitHub/giggles/downloads/laughter_segments.jsonl \
  --input-audio-dir ~/Documents/GitHub/giggles/downloads \
  --out-dir out \
  --context-seconds 3 \
  --prob-threshold 0.60 \
  --max-clips 500 \
  --verbose
"""

from __future__ import annotations
import argparse, json, sys, os, shutil, subprocess, hashlib
from pathlib import Path
from typing import Dict, List, Optional, Any

# ---------- FFmpeg resolution ----------

def resolve_ffmpeg() -> Optional[str]:
    # 1) explicit env
    env_bin = os.environ.get("FFMPEG_BINARY")
    if env_bin and Path(env_bin).exists():
        return env_bin
    # 2) PATH
    w = shutil.which("ffmpeg")
    if w:
        return w
    # 3) imageio_ffmpeg (best-effort)
    try:
        import imageio_ffmpeg  # type: ignore
        p = imageio_ffmpeg.get_ffmpeg_exe()
        if p and Path(p).exists():
            return p
    except Exception:
        pass
    return None

# ---------- IO helpers ----------

def load_segments(jsonl_path: Path) -> List[Dict[str, Any]]:
    items: List[Dict[str, Any]] = []
    with jsonl_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            # If it’s a per-file record with "segments", explode it
            if isinstance(obj, dict) and "file" in obj and "segments" in obj:
                src = obj["file"]
                for seg in obj.get("segments", []):
                    if "start" in seg and "end" in seg:
                        items.append({
                            "file": src,
                            "start": float(seg["start"]),
                            "end": float(seg["end"]),
                            "avg_prob": float(seg.get("avg_prob", seg.get("prob", 0.0)))
                        })
            else:
                # Flat segment
                if all(k in obj for k in ("file", "start", "end")):
                    obj["start"] = float(obj["start"])
                    obj["end"] = float(obj["end"])
                    obj["avg_prob"] = float(obj.get("avg_prob", obj.get("prob", 0.0)))
                    items.append(obj)
    return items

def safe_id(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:12]

def sanitize(stem: str) -> str:
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in stem)

# ---------- Snippet extraction ----------

def make_snippet(
    ffmpeg: Optional[str],
    src_path: Path,
    start: float,
    end: float,
    out_path: Path,
    sr: int = 16000
) -> bool:
    """
    Cut [start, end] (seconds) to out_path as mono wav. Returns True on success.
    """
    if not ffmpeg:
        return False
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-hide_banner", "-loglevel", "error",
        "-ss", f"{max(0.0, start):.3f}",
        "-to", f"{max(start, end):.3f}",
        "-i", str(src_path),
        "-ac", "1", "-ar", str(sr),
        "-y", str(out_path)
    ]
    try:
        subprocess.run(cmd, check=True)
        return out_path.exists() and out_path.stat().st_size > 0
    except subprocess.CalledProcessError:
        return False

# ---------- HTML report ----------

REPORT_HTML = """<!doctype html>
<html>
<head>
<meta charset="utf-8"/>
<title>Giggles Eval</title>
<style>
  body { font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 24px; }
  table { border-collapse: collapse; width: 100%; }
  th, td { border-bottom: 1px solid #ddd; padding: 8px; vertical-align: top; }
  th { position: sticky; top: 0; background: #fafafa; }
  .prob { font-variant-numeric: tabular-nums; }
  textarea { width: 100%; min-height: 56px; }
  .controls { margin: 12px 0; display: flex; gap: 12px; align-items: center; }
  .badge { display: inline-block; padding: 2px 6px; border-radius: 6px; background:#eef; color:#224; font-size: 12px; }
</style>
</head>
<body>
<h1>Giggles Eval</h1>
<p class="badge">Local, static report — no server or network</p>

<div class="controls">
  <label>Threshold filter:
    <input type="number" step="0.01" min="0" max="1" id="th" value="0">
  </label>
  <button onclick="applyThreshold()">Apply</button>
  <button onclick="exportJSONL()">Export annotations (JSONL)</button>
</div>

<table id="clips">
  <thead>
    <tr>
      <th>#</th>
      <th>Play</th>
      <th>Prob</th>
      <th>Span (s)</th>
      <th>Source File</th>
      <th>Comment</th>
      <th>Keep?</th>
    </tr>
  </thead>
  <tbody></tbody>
</table>

<script>
const DATA = __DATA__;
const tbody = document.querySelector("#clips tbody");

function row(item, idx){
  const tr = document.createElement("tr");
  tr.dataset.idx = idx;

  const tdIdx = document.createElement("td");
  tdIdx.textContent = idx+1;

  const tdPlay = document.createElement("td");
  if (item.snippet) {
    const audio = document.createElement("audio");
    audio.controls = true;
    audio.src = item.snippet;
    audio.preload = "none";
    tdPlay.appendChild(audio);
  } else {
    tdPlay.textContent = "(no snippet)";
  }

  const tdProb = document.createElement("td");
  tdProb.className = "prob";
  tdProb.textContent = (item.avg_prob ?? 0).toFixed(3);

  const tdSpan = document.createElement("td");
  tdSpan.textContent = `${item.start.toFixed(2)} – ${item.end.toFixed(2)} (${(item.end-item.start).toFixed(2)}s)`;

  const tdFile = document.createElement("td");
  tdFile.textContent = item.file;

  const tdComment = document.createElement("td");
  const ta = document.createElement("textarea");
  ta.value = item.comment ?? "";
  ta.addEventListener("input", e => { item.comment = ta.value; });
  tdComment.appendChild(ta);

  const tdKeep = document.createElement("td");
  const cb = document.createElement("input");
  cb.type = "checkbox";
  cb.checked = item.keep ?? true;
  cb.addEventListener("change", e => { item.keep = cb.checked; });
  tdKeep.appendChild(cb);

  [tdIdx, tdPlay, tdProb, tdSpan, tdFile, tdComment, tdKeep].forEach(td => tr.appendChild(td));
  return tr;
}

function render(data){
  tbody.innerHTML = "";
  data.forEach((it, i) => tbody.appendChild(row(it, i)));
}

function applyThreshold(){
  const th = parseFloat(document.getElementById("th").value || "0");
  const filtered = DATA.filter(d => (d.avg_prob ?? 0) >= th);
  render(filtered);
}

function exportJSONL(){
  const lines = DATA.map(d => JSON.stringify(d));
  const blob = new Blob([lines.join("\\n") + "\\n"], {type: "application/json"});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = "annotations.jsonl";
  a.click();
  URL.revokeObjectURL(a.href);
}

render(DATA);
</script>
</body>
</html>
"""

# ---------- Main pipeline ----------

def main():
    ap = argparse.ArgumentParser(description="Build a human-eval report for laughter spans (no ML).")
    ap.add_argument("--segments-jsonl", required=True, type=Path, help="Path to segments JSONL.")
    ap.add_argument("--input-audio-dir", type=Path, default=None, help="Directory with original audio (to resolve relative paths).")
    ap.add_argument("--out-dir", type=Path, default=Path("out"), help="Output directory.")
    ap.add_argument("--context-seconds", type=float, default=3.0, help="Pad this many seconds before/after each span.")
    ap.add_argument("--prob-threshold", type=float, default=0.0, help="Keep only segments with avg_prob >= threshold.")
    ap.add_argument("--max-clips", type=int, default=1000000, help="Cap how many segments to include.")
    ap.add_argument("--snip-rate", type=int, default=16000, help="Sample rate for snippets.")
    ap.add_argument("--verbose", action="store_true", help="Verbose logging.")
    args = ap.parse_args()

    out_dir = args.out_dir
    snips_dir = out_dir / "snippets"
    out_dir.mkdir(parents=True, exist_ok=True)
    snips_dir.mkdir(parents=True, exist_ok=True)

    ffmpeg = resolve_ffmpeg()
    if args.verbose:
        print(f"FFmpeg: {ffmpeg or '(not found — snippets will be skipped)'}")

    raw_items = load_segments(args.segments_jsonl)
    if args.verbose:
        print(f"Loaded {len(raw_items)} segments from {args.segments_jsonl}")

    # Normalize / filter
    items: List[Dict[str, Any]] = []
    for seg in raw_items:
        prob = float(seg.get("avg_prob", 0.0))
        if prob < args.prob_threshold:
            continue
        src = Path(seg["file"])
        if not src.is_absolute() and args.input_audio_dir:
            candidate = args.input_audio_dir / src
        else:
            candidate = src
        items.append({
            "file": str(candidate),
            "start": float(seg["start"]),
            "end": float(seg["end"]),
            "avg_prob": prob
        })
        if len(items) >= args.max_clips:
            break

    if args.verbose:
        print(f"Kept {len(items)} segments after threshold/cap")

    # Generate snippets and trace
    trace_path = out_dir / "trace.jsonl"
    n_ok = 0
    with trace_path.open("w", encoding="utf-8") as fout:
        for idx, it in enumerate(items, 1):
            src = Path(it["file"])
            start = max(0.0, it["start"] - args.context_seconds)
            end   = max(start, it["end"] + args.context_seconds)

            stem = sanitize(src.stem)
            seg_id = safe_id(f"{src}::{start:.3f}-{end:.3f}")
            out_snip = snips_dir / f"{stem}__{seg_id}.wav"
            made = False
            if src.exists():
                made = make_snippet(ffmpeg, src, start, end, out_snip, sr=args.snip_rate)
            if args.verbose:
                print(f"[{idx:05d}] {src.name} {start:.2f}-{end:.2f}s  prob={it['avg_prob']:.3f}  -> {'OK' if made else 'SKIP'}")

            rec = {
                "id": seg_id,
                "file": str(src),
                "start": it["start"],
                "end": it["end"],
                "avg_prob": it["avg_prob"],
                "context_start": start,
                "context_end": end,
                "snippet": str(out_snip.relative_to(out_dir)) if made else "",
                "comment": "",
                "keep": True
            }
            fout.write(json.dumps(rec) + "\n")
            if made:
                n_ok += 1

    # Build HTML with embedded DATA (relative paths from out_dir)
    data: List[Dict[str, Any]] = []
    with trace_path.open("r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                data.append(json.loads(line))

    html_path = out_dir / "report.html"
    html = REPORT_HTML.replace("__DATA__", json.dumps(data))
    html_path.write_text(html, encoding="utf-8")

    print(f"\nDone.")
    print(f"  Trace:   {trace_path}")
    print(f"  Snips:   {snips_dir}  ({n_ok} audio files)")
    print(f"  Report:  {html_path}\n")
    print("Open the report in your browser, filter by probability, play clips, add comments,")
    print("and click 'Export annotations (JSONL)' to download your labeled file.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nInterrupted.")
        sys.exit(1)
