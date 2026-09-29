from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path


def _filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def render_short(audio: Path, title: str, language: str, output: Path) -> Path:
    """Render a simple 9:16 news short with a title card and the generated narration."""
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg is required for rendering; install it with Homebrew or your OS package manager")
    if not audio.exists():
        raise RuntimeError(f"voice file missing: {audio}")
    output.parent.mkdir(parents=True, exist_ok=True)
    title_file = output.with_suffix(".title.txt")
    title_file.write_text(title, encoding="utf-8")
    filters = subprocess.run(["ffmpeg", "-filters"], capture_output=True, text=True).stdout
    drawtext = (
        f"drawtext=textfile={_filter_path(title_file)}:fontcolor=white:fontsize=64:"
        "x=(w-text_w)/2:y=(h-text_h)/2:line_spacing=12:box=1:boxcolor=black@0.4:boxborderw=24"
    )
    command = [
        "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=0x111311:s=1080x1920:r=30",
        "-i", str(audio), "-shortest", *( ["-vf", drawtext] if "drawtext" in filters else [] ), "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-movflags", "+faststart", str(output),
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    title_file.unlink(missing_ok=True)
    if result.returncode:
        raise RuntimeError(f"ffmpeg render failed: {result.stderr[-800:]}")
    return output


def _render_remotion(props: dict, output: Path) -> Path | None:
    """Use the Remotion template when its local Node install is available."""
    if os.getenv("REMOTION_RENDER", "0") != "1":
        return None
    render_dir = Path(__file__).resolve().parent.parent / "render"
    binary = render_dir / "node_modules" / ".bin" / "remotion"
    if not binary.exists():
        raise RuntimeError("REMOTION_RENDER=1 but render/node_modules is missing; run `cd render && npm install`")
    props_path = output.with_suffix(".props.json")
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(binary), "render", "src/index.ts", "NewsShort", str(output), "--props", str(props_path), "--codec", "h264", "--width", "1080", "--height", "1920", "--fps", "30"]
    result = subprocess.run(command, cwd=render_dir, capture_output=True, text=True)
    props_path.unlink(missing_ok=True)
    if result.returncode:
        raise RuntimeError(f"Remotion render failed: {result.stderr[-1000:]}")
    return output


def render_bilingual(topic_dir: Path) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    for language in ("en", "hi"):
        spec = json.loads((topic_dir / f"spec_{language}.json").read_text())
        outputs[language] = render_short(
            topic_dir / "voice" / f"voice_{language}.wav",
            spec["title"],
            language,
            topic_dir / f"short_{language}.mp4",
        )
    return outputs


def _concat_audio(files: list[Path], output: Path) -> Path:
    listing = output.with_suffix(".concat.txt")
    listing.write_text("\n".join(f"file '{str(path).replace(chr(39), chr(39) + chr(92) + chr(39) + chr(39))}'" for path in files))
    result = subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(output)], capture_output=True, text=True)
    listing.unlink(missing_ok=True)
    if result.returncode:
        raise RuntimeError(f"ffmpeg audio concat failed: {result.stderr[-800:]}")
    return output


def render_platforms(topic_dir: Path) -> dict[str, Path]:
    outputs: dict[str, Path] = {}
    for language in ("en", "hi"):
        for platform in ("instagram", "youtube"):
            spec = json.loads((topic_dir / f"spec_{language}_{platform}.json").read_text())
            manifest = json.loads((topic_dir / f"voice_{language}_{platform}.json").read_text())
            audio = topic_dir / f"audio_{language}_{platform}.wav"
            _concat_audio([topic_dir / scene["file"] for scene in manifest["scenes"]], audio)
            output = topic_dir / f"short_{language}_{platform}.mp4"
            props = {"title": spec["title"], "language": language, "audio": str(audio.resolve()), "scenes": spec["scenes"], "assets": str((topic_dir / "assets").resolve())}
            outputs[f"{language}_{platform}"] = _render_remotion(props, output) or render_short(audio, spec["title"], language, output)
    return outputs
