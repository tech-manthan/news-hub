from __future__ import annotations

import json
from pathlib import Path


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
                    try:
                        page.goto(source["url"], wait_until="domcontentloaded", timeout=30_000)
                        path = asset_dir / f"source_{index}.png"
                        page.screenshot(path=str(path), full_page=False)
                        assets.append({"id": f"source_{index}", "type": "image", "file": str(path.relative_to(output_dir)), "source_id": source["id"], "url": source["url"]})
                    except Exception as exc:
                        assets.append({"id": f"source_{index}", "type": "error", "source_id": source["id"], "error": str(exc)})
            finally:
                browser_instance.close()
    path = output_dir / "assets.json"
    path.write_text(json.dumps({"assets": assets}, indent=2, ensure_ascii=False))
    return path
