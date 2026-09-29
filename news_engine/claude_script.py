from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .models import Topic
from .spec import LanguageSpec, platform_variant, validate_spec

SYSTEM = """You write factual 30-45 second vertical news shorts from supplied research. Use only the supplied facts.
No invented numbers, claims, quotes, or causal explanations. Spoken narration must sound natural and concise.
The first scene must state the payoff immediately. The final scene is a one-sentence platform-specific CTA.
English and Hindi specs are generated separately from the same source IDs. Hindi narration must be Devanagari,
but proper names and technical terms may remain in Latin script. Avoid emojis and markdown in narration."""


def _schema() -> dict:
    return {"type": "object", "properties": LanguageSpec.model_json_schema()["properties"], "required": list(LanguageSpec.model_json_schema()["required"]), "additionalProperties": False}


def _prompt(topic: Topic, language: str) -> str:
    sources = "\n".join(f"[{s.id}] {s.publisher}: {s.title}\n{s.description}\n{s.url}" for s in topic.sources)
    return f"""Create a {language} news short about this topic.

Headline: {topic.headline}
Summary: {topic.summary}
Confidence: {topic.confidence}
Source IDs must be exactly: {[s.id for s in topic.sources]}

RESEARCH SOURCES:
{sources}

Rules:
- 5 to 7 scenes; first hook_stat and last cta.
- Use at least one screenshot_scroll or image scene.
- Total narration 70-120 words.
- Every scene source_ids must refer only to supplied IDs.
- Instagram CTA should invite following/commenting; YouTube CTA should invite subscribing.
- YouTube metadata is SEO-oriented; Instagram caption is conversational.
"""


def _call_claude(prompt: str, model: str) -> dict:
    command = ["claude", "-p", "--output-format", "json", "--json-schema", json.dumps(_schema()), "--system-prompt", SYSTEM, "--tools", "", "--no-session-persistence", "--model", model]
    env = {key: value for key, value in os.environ.items() if key != "ANTHROPIC_API_KEY"}
    with tempfile.TemporaryDirectory() as cwd:
        result = subprocess.run(command, input=prompt, capture_output=True, text=True, cwd=cwd, env=env, timeout=600)
    if result.returncode:
        raise RuntimeError(f"claude exited {result.returncode}: {(result.stderr or result.stdout)[-800:]}")
    payload = json.loads(result.stdout)
    if payload.get("is_error") or not payload.get("structured_output"):
        raise RuntimeError("claude returned no structured output")
    return payload["structured_output"]


def write_specs(topic: Topic, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    model = os.getenv("SCRIPT_MODEL", "opus")
    expected = {source.id for source in topic.sources}
    paths: dict[str, Path] = {}
    for language in ("en", "hi"):
        prompt = _prompt(topic, language)
        errors: list[str] = []
        spec: LanguageSpec | None = None
        for attempt in range(2):
            raw = _call_claude(prompt if not errors else prompt + "\n\nFix these validation errors:\n- " + "\n- ".join(errors), model)
            try:
                candidate = LanguageSpec.model_validate(raw)
                errors = validate_spec(candidate, expected)
                if not errors:
                    spec = candidate
                    break
            except Exception as exc:
                errors = [str(exc)]
        if spec is None:
            raise RuntimeError(f"{language} script failed validation: {'; '.join(errors)}")
        for platform in ("instagram", "youtube"):
            path = output_dir / f"spec_{language}_{platform}.json"
            path.write_text(json.dumps(platform_variant(spec, platform).model_dump(), indent=2, ensure_ascii=False))
            paths[f"{language}_{platform}"] = path
    return paths
