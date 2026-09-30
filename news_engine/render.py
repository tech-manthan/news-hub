from __future__ import annotations

import json
import os
import shutil
import subprocess
import uuid
from pathlib import Path


def render_settings() -> dict[str, str]:
    return {
        "bgPreset": os.getenv("NEWS_BG_PRESET", "midnight"),
        "font": os.getenv("NEWS_FONT", "inter"),
        "template": os.getenv("NEWS_TEMPLATE", "editorial"),
    }


def _filter_path(path: Path) -> str:
    return str(path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "\\'")


def _remotion_static_props(topic_dir: Path, audio: Path, public_name: str | None = None) -> dict[str, str]:
    """Return paths addressed through Remotion's public static-file server."""
    prefix = Path("news-engine") / (public_name or topic_dir.name)
    return {"audio": (prefix / audio.name).as_posix(), "assets": (prefix / "assets").as_posix()}


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


def _render_remotion(props: dict, output: Path, topic_dir: Path) -> Path | None:
    """Use the Remotion template when its local Node install is available."""
    if os.getenv("REMOTION_RENDER", "0") != "1":
        return None
    render_dir = Path(__file__).resolve().parent.parent / "render"
    binary = render_dir / "node_modules" / ".bin" / "remotion"
    if not binary.exists():
        raise RuntimeError("REMOTION_RENDER=1 but render/node_modules is missing; run `cd render && npm install`")
    # Isolate concurrent manual and automated renders so one job cannot remove
    # another job's audio while Remotion is still reading it.
    public_name = f"{topic_dir.name}-{output.stem}-{uuid.uuid4().hex[:8]}"
    public_root = render_dir / "public" / "news-engine" / public_name
    props_path = output.with_suffix(".props.json")
    public_root.parent.mkdir(parents=True, exist_ok=True)
    shutil.rmtree(public_root, ignore_errors=True)
    public_root.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(props["audio"]), public_root / Path(props["audio"]).name)
    assets = topic_dir / "assets"
    if assets.exists():
        shutil.copytree(assets, public_root / "assets", dirs_exist_ok=True)
    remotion_props = {**props, **_remotion_static_props(topic_dir, Path(props["audio"]), public_name)}
    props_path.write_text(json.dumps(remotion_props, ensure_ascii=False), encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    command = [str(binary), "render", "src/index.ts", "NewsShort", str(output), "--props", str(props_path), "--codec", "h264", "--width", "1080", "--height", "1920", "--fps", "30"]
    try:
        result = subprocess.run(command, cwd=render_dir, capture_output=True, text=True)
        if result.returncode:
            raise RuntimeError(f"Remotion render failed: {result.stderr[-1000:]}")
        return output
    finally:
        props_path.unlink(missing_ok=True)
        shutil.rmtree(public_root, ignore_errors=True)


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
    asset_ids = sorted(path.stem for path in (topic_dir / "assets").glob("*.png"))
    asset_sources = {}
    assets_manifest = topic_dir / "assets.json"
    if assets_manifest.exists():
        asset_sources = {item.get("source_id"): item.get("id") for item in json.loads(assets_manifest.read_text()).get("assets", []) if item.get("id")}
    for language in ("en", "hi"):
        for platform in ("instagram", "youtube"):
            spec = json.loads((topic_dir / f"spec_{language}_{platform}.json").read_text())
            manifest = json.loads((topic_dir / f"voice_{language}_{platform}.json").read_text())
            audio = topic_dir / f"audio_{language}_{platform}.wav"
            _concat_audio([topic_dir / scene["file"] for scene in manifest["scenes"]], audio)
            output = topic_dir / f"short_{language}_{platform}.mp4"
            voice_scenes = manifest.get("scenes", [])
            scenes = []
            for index, scene in enumerate(spec["scenes"]):
                voice_scene = voice_scenes[index] if index < len(voice_scenes) else {}
                scene = dict(scene)
                if not scene.get("asset_id") and scene.get("type") in ("image", "screenshot_scroll") and asset_ids:
                    scene["asset_id"] = next((asset_sources.get(source_id) for source_id in scene.get("source_ids", []) if asset_sources.get(source_id)), asset_ids[index % len(asset_ids)])
                scenes.append({**scene, "duration": voice_scene.get("duration", 4), "words": voice_scene.get("words", [])})
            props = {"title": spec["title"], "language": language, "platform": platform, "audio": str(audio.resolve()), "scenes": scenes, "assets": str((topic_dir / "assets").resolve()), **render_settings()}
            outputs[f"{language}_{platform}"] = _render_remotion(props, output, topic_dir) or render_short(audio, spec["title"], language, output)
    return outputs
