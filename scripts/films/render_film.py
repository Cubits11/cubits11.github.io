#!/usr/bin/env python3
"""Render a film deterministically: seek every frame, capture pixels, encode.

    python3 scripts/films/render_film.py <slug> [<slug> ...] [--format master|vertical|square|all]

Nothing is recorded in real time. The page exposes window.__film.seek(t); this
script walks the timeline frame by frame over the Chrome DevTools Protocol,
writes the frames to a temporary directory OUTSIDE the repository, encodes an
H.264 master, keeps a poster, five review stills (0/25/50/75/100 %), a contact
sheet, and one still per declared claim frame — then deletes the frames.

A render receipt records what was rendered from what: the git HEAD, sha256 of
the film source, the runtime, and the facts file; the frame count, duration,
resolution; a digest over every frame's sha256; text overflows reported by the
runtime; and a determinism check (five sampled frames re-captured after the
pass and compared byte-for-byte).

Requires: Google Chrome (installed), and a venv with playwright + imageio-ffmpeg
(the bundled ffmpeg is used; no system ffmpeg is needed). Frames are captured
at ~50 ms each, so a 30-second film renders in about a minute.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import http.server
import json
import os
import shutil
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FILMS = ROOT / "films"
CHROME_ARGS = ["--force-color-profile=srgb", "--font-render-hinting=none", "--disable-gpu-vsync",
               "--hide-scrollbars", "--disable-lcd-text"]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return sha256_bytes(p.read_bytes())


def git_head() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
    except Exception:
        return "unknown"


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass


def serve_root() -> tuple[socketserver.TCPServer, int]:
    handler = lambda *a, **kw: QuietHandler(*a, directory=str(ROOT), **kw)  # noqa: E731
    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), handler)
    srv.daemon_threads = True
    port = srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, port


def ffmpeg_exe() -> str:
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def encode(ff: str, frames: Path, fps: int, out: Path, crf: int) -> None:
    subprocess.run([ff, "-y", "-hide_banner", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames / "f%05d.png"),
                    "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", str(out)], check=True)


def probe_duration(ff: str, mp4: Path) -> float | None:
    """Duration via ffmpeg's own stderr (no ffprobe in the imageio bundle)."""
    r = subprocess.run([ff, "-hide_banner", "-i", str(mp4)], capture_output=True, text=True)
    for ln in r.stderr.splitlines():
        ln = ln.strip()
        if ln.startswith("Duration:"):
            hms = ln.split()[1].rstrip(",")
            h, m, s = hms.split(":")
            return int(h) * 3600 + int(m) * 60 + float(s)
    return None


def save_still(frame_png: Path, out_jpg: Path) -> None:
    """Review stills are JPEG (quality 90): a fifth of the PNG bytes, and pixels are graded by eye, not by hash."""
    from PIL import Image
    Image.open(frame_png).convert("RGB").save(out_jpg, "JPEG", quality=90, optimize=True)


def contact_sheet(stills: list[Path], out: Path, labels: list[str], thumb: int = 640) -> None:
    from PIL import Image, ImageDraw
    ims = [Image.open(p).convert("RGB") for p in stills]
    if not ims:
        return
    w, h = ims[0].size
    tw = thumb
    th = round(h * tw / w)
    cols = min(3, len(ims))
    rows = (len(ims) + cols - 1) // cols
    sheet = Image.new("RGB", (cols * tw + (cols + 1) * 12, rows * (th + 34) + 12), "#0B0F0A")
    d = ImageDraw.Draw(sheet)
    for i, im in enumerate(ims):
        x = 12 + (i % cols) * (tw + 12)
        y = 12 + (i // cols) * (th + 34)
        sheet.paste(im.resize((tw, th)), (x, y))
        d.text((x, y + th + 8), labels[i], fill="#9AA391")
    sheet.save(out, "JPEG", quality=85, optimize=True)


def render_one(slug: str, fmt: str, port: int, args, ff: str) -> dict:
    from playwright.sync_api import sync_playwright

    film_dir = FILMS / slug
    film_html = film_dir / "film.html"
    if not film_html.exists():
        raise SystemExit(f"no film at {film_html.relative_to(ROOT)}")
    renders = film_dir / "renders"
    stills_dir = renders / "stills"
    renders.mkdir(parents=True, exist_ok=True)
    stills_dir.mkdir(parents=True, exist_ok=True)
    url = f"http://127.0.0.1:{port}/films/{slug}/film.html?capture=1&format={fmt}"
    tmp = Path(tempfile.mkdtemp(prefix=f"film-{slug}-{fmt}-"))
    frames = tmp / "frames"
    frames.mkdir()
    t_start = time.time()
    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(channel="chrome", args=CHROME_ARGS)
            page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
            errors: list[str] = []
            page.on("pageerror", lambda e: errors.append(str(e)))
            # resource 404s are reported by URL below (favicon excluded); other console errors are real
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" and "Failed to load resource" not in m.text else None)
            page.on("response", lambda r: errors.append(f"{r.status} {r.url}") if r.status >= 400 and not r.url.endswith("favicon.ico") else None)
            page.goto(url, wait_until="load")
            page.wait_for_function("window.__film && window.__film.ready", timeout=30000)
            meta = page.evaluate("window.__film.meta")
            W, H = meta["width"], meta["height"]
            page.set_viewport_size({"width": W, "height": H})
            fps = args.fps or meta["fps"]
            total = round(meta["duration"] * fps) + 1  # inclusive of the final frame
            cdp = page.context.new_cdp_session(page)
            page.evaluate("window.__film.resetOverflows()")
            hashes: list[str] = []
            print(f"  {slug} [{fmt}] {W}x{H} @ {fps}fps — {total} frames", flush=True)
            for i in range(total):
                page.evaluate("t => window.__film.seek(t)", i / fps)
                data = base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True})["data"])
                (frames / f"f{i:05d}.png").write_bytes(data)
                hashes.append(sha256_bytes(data))
                if i % (fps * 5) == 0 and i:
                    print(f"    frame {i}/{total}", flush=True)
            overflows = page.evaluate("window.__film.overflows()")
            facts_used = page.evaluate("window.__film.factsUsed()")
            # determinism: re-capture five sampled frames and compare bytes
            sample = sorted({0, total // 4, total // 2, 3 * total // 4, total - 1})
            identical = True
            for i in sample:
                page.evaluate("t => window.__film.seek(t)", i / fps)
                data = base64.b64decode(cdp.send("Page.captureScreenshot", {"format": "png", "optimizeForSpeed": True})["data"])
                if sha256_bytes(data) != hashes[i]:
                    identical = False
            chrome_version = browser.version
            browser.close()
        if errors:
            raise SystemExit(f"page errors during render of {slug}: {errors[:3]}")

        stem = f"{slug}__{fmt}"
        mp4 = renders / f"{stem}.mp4"
        encode(ff, frames, fps, mp4, args.crf)
        # stills: 0/25/50/75/100 %, poster, claim frames
        marks = [("open", 0), ("q1", total // 4), ("mid", total // 2), ("q3", 3 * total // 4), ("end", total - 1)]
        still_paths, labels = [], []
        for name, i in marks:
            p = stills_dir / f"{fmt}-{name}.jpg"
            save_still(frames / f"f{i:05d}.png", p)
            still_paths.append(p); labels.append(f"{name} · t={i / fps:.2f}s")
        poster_i = min(total - 1, round(meta["poster_t"] * fps))
        poster = renders / f"{stem}.poster.png"
        shutil.copyfile(frames / f"f{poster_i:05d}.png", poster)
        claim_stills = []
        for n, cf in enumerate(meta.get("claim_frames", []), 1):
            i = min(total - 1, round(float(cf["t"]) * fps))
            p = stills_dir / f"{fmt}-claim-{n:02d}.jpg"
            save_still(frames / f"f{i:05d}.png", p)
            claim_stills.append({"n": n, "t": cf["t"], "label": cf.get("label", ""), "still": str(p.relative_to(film_dir))})
        contact_sheet(still_paths, renders / f"{stem}.sheet.jpg", labels)
        # phone previews: the feed shows a square at roughly 390 CSS px; the acceptance
        # test for essential text is practical legibility on THESE files, not on the master
        phone = []
        if fmt == "square":
            from PIL import Image
            phone_dir = stills_dir
            for p_src in still_paths + [stills_dir / c["still"].split("/")[-1] for c in claim_stills]:
                out_p = phone_dir / f"phone-{p_src.name}"
                Image.open(p_src).convert("RGB").resize((390, 390), Image.LANCZOS).save(out_p, "JPEG", quality=92)
                phone.append(str(out_p.relative_to(film_dir)))
            sheet_in = [film_dir / c["still"] for c in claim_stills]
            contact_sheet(sheet_in, renders / f"{stem}.phone-sheet.jpg", [c["label"][:60] for c in claim_stills], thumb=390)

        receipt = {
            "film": slug, "format": fmt, "title": meta["title"],
            "rendered_from_head": git_head(), "rendered_on": date.today().isoformat(),
            "inputs": {
                "film.html": sha256_file(film_html),
                "films/lib/film.js": sha256_file(FILMS / "lib" / "film.js"),
                "films/lib/tokens.css": sha256_file(FILMS / "lib" / "tokens.css"),
                "films/data/facts.json": sha256_file(FILMS / "data" / "facts.json"),
            },
            "runtime": {"chrome": chrome_version, "ffmpeg": Path(ff).name, "crf": args.crf},
            "fps": fps, "frames": total, "duration_s": round(meta["duration"], 3),
            "width": W, "height": H,
            "frames_digest": sha256_bytes("".join(hashes).encode()),
            "determinism": {"sampled_frames": len(sample), "identical": identical},
            "text_overflows": overflows,
            "facts_used": facts_used,
            "outputs": {
                "master": str(mp4.relative_to(film_dir)), "master_sha256": sha256_file(mp4), "master_bytes": mp4.stat().st_size,
                "master_duration_probe_s": probe_duration(ff, mp4),
                "poster": str(poster.relative_to(film_dir)), "poster_t": meta["poster_t"],
                "stills": [str(p.relative_to(film_dir)) for p in still_paths],
                "claim_frames": claim_stills,
                "phone_previews": phone,
            },
            "render_seconds": round(time.time() - t_start, 1),
        }
        (renders / f"{stem}.receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
        print(f"  wrote {mp4.relative_to(ROOT)} ({mp4.stat().st_size / 1e6:.2f} MB) · determinism {'ok' if identical else 'FAILED'} · overflows {len(overflows)} · {receipt['render_seconds']}s")
        return receipt
    finally:
        if args.keep_frames:
            print(f"  frames kept at {frames}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("slugs", nargs="+")
    ap.add_argument("--format", default="master", choices=["master", "vertical", "square", "all"])
    ap.add_argument("--fps", type=int, default=None, help="override the film's declared fps")
    ap.add_argument("--crf", type=int, default=20)
    ap.add_argument("--keep-frames", action="store_true")
    args = ap.parse_args()
    ff = ffmpeg_exe()
    srv, port = serve_root()
    formats = ["master", "vertical"] if args.format == "all" else [args.format]
    bad = 0
    try:
        for slug in args.slugs:
            for fmt in formats:
                r = render_one(slug, fmt, port, args, ff)
                if not r["determinism"]["identical"] or r["text_overflows"]:
                    bad += 1
    finally:
        srv.shutdown()
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
