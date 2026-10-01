from __future__ import annotations

import html
import json
from pathlib import Path
from urllib.parse import quote


def write_assets(research_path: Path, output_dir: Path, *, browser: bool = True) -> Path:
    research = json.loads(research_path.read_text())
    asset_dir = output_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    assets: list[dict] = []
    if browser:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:
            raise RuntimeError("Assets need Playwright: install `python -m pip install -e '.[browser]'` and `python -m playwright install chromium`") from exc
        with sync_playwright() as playwright:
            browser_instance = playwright.chromium.launch(headless=True)
            page = browser_instance.new_page(viewport={"width": 1280, "height": 900}, color_scheme="dark")
            try:
                for index, source in enumerate(research.get("sources", [])):
                    path = asset_dir / f"source_{index}.png"
                    try:
                        page.goto(source["url"], wait_until="domcontentloaded", timeout=30_000)
                        body = page.locator("body").inner_text(timeout=5).strip()
                        if len(body) < 80:
                            raise RuntimeError("source page returned no readable article body")
                        page.screenshot(path=str(path), full_page=False)
                        assets.append({"id": f"source_{index}", "type": "image", "file": str(path.relative_to(output_dir)), "source_id": source["id"], "url": source["url"]})
                    except Exception as exc:
                        card = f"""<!doctype html><html><head><meta charset='utf-8'></head><body style='margin:0;background:linear-gradient(135deg,#101a2b 0%,#0a0e16 58%,#132a28 100%);color:#f4f7f2;font-family:Arial,sans-serif;padding:70px;overflow:hidden'><div style='position:absolute;right:-100px;top:80px;width:420px;height:420px;border-radius:50%;background:#8bf06c18'></div><div style='font-size:28px;letter-spacing:5px;color:#8bf06c'>NEWS ENGINE · SOURCE</div><div style='margin-top:150px;font-size:24px;color:#8bf06c;font-weight:700;letter-spacing:2px'>{html.escape(source.get('publisher', 'Verified source')).upper()}</div><div style='position:absolute;right:70px;top:275px;font-size:210px;line-height:1;color:#ffffff0c;font-weight:900'>01</div><h1 style='font-size:64px;line-height:1.05;margin:24px 0;max-width:1030px'>{html.escape(source.get('title', 'Source headline'))}</h1><p style='font-size:32px;line-height:1.35;color:#c8d0dc;max-width:980px'>{html.escape(source.get('description', 'Reviewed source evidence'))}</p><div style='position:absolute;bottom:70px;font-size:20px;color:#aab5c6;letter-spacing:2px'>VERIFIED SOURCE · REVIEWED BEFORE SCRIPTING</div></body></html>"""
                        page.goto("data:text/html;charset=utf-8," + quote(card), wait_until="load")
                        page.screenshot(path=str(path), full_page=False)
                        assets.append({"id": f"source_{index}", "type": "image", "file": str(path.relative_to(output_dir)), "source_id": source["id"], "url": source["url"], "fallback": True, "error": str(exc)})
            finally:
                browser_instance.close()
    path = output_dir / "assets.json"
    path.write_text(json.dumps({"assets": assets}, indent=2, ensure_ascii=False))
    return path
