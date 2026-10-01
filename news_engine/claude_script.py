from __future__ import annotations

import json
import os
import subprocess
import tempfile
from copy import deepcopy
from pathlib import Path

from .models import Topic
from .spec import LanguageSpec, platform_variant, validate_spec

SYSTEM = """You write factual 30-45 second vertical news shorts from supplied research, using an attention-first newsroom and marketing-editor mindset. Use only the supplied facts.
No invented numbers, claims, quotes, or causal explanations. Spoken narration must sound natural, specific, and concise.
Use a Hook → Hold → Payoff structure: make the promise or consequence clear in the first 1-2 seconds, reveal a new verified beat in every following scene, then close with a satisfying implication and one short platform-specific CTA.
Choose one story engine that fits the evidence: a surprising reveal, a conflict between two forces, a consequence for ordinary people, a countdown of verified developments, a myth-versus-fact correction, or a "what changes next" briefing. Make the viewer care by naming the human stake, decision, risk, or opportunity—without manufacturing emotion.
The first scene must state the payoff immediately. The final scene is a one-sentence platform-specific CTA.
English and Hindi specs are generated separately from the same source IDs. Avoid emojis and markdown in narration.
For Hindi, write all narration, headlines, bullets, and CTAs in natural Devanagari Hindi. Preserve only
unavoidable proper names, brand names, and uppercase acronyms such as AI, OpenAI, Google, or The Guardian;
translate ordinary English words such as tech, news, subscribe, runaway, intelligence, and godfathers."""


def _schema() -> dict:
    """Return a Claude-compatible schema with local Pydantic refs inlined.

    Claude's ``--json-schema`` validator rejects Pydantic's otherwise valid
    ``$defs``/``$ref`` form (for example ``#/$defs/Scene``), so the schema
    passed over the CLI boundary must be self-contained.
    """
    schema = LanguageSpec.model_json_schema()
    definitions = schema.get("$defs", {})

    def expand(value: object, stack: tuple[str, ...] = ()) -> object:
        if isinstance(value, list):
            return [expand(item, stack) for item in value]
        if not isinstance(value, dict):
            return value
        ref = value.get("$ref")
        if isinstance(ref, str) and ref.startswith("#/$defs/"):
            name = ref.removeprefix("#/$defs/")
            if name in stack:
                raise ValueError(f"recursive JSON schema definition: {name}")
            expanded = expand(deepcopy(definitions[name]), stack + (name,))
            siblings = {key: expand(item, stack) for key, item in value.items() if key != "$ref"}
            if isinstance(expanded, dict):
                expanded.update(siblings)
            return expanded
        return {key: expand(item, stack) for key, item in value.items() if key != "$defs"}

    return expand(schema)


def _prompt(topic: Topic, language: str) -> str:
    sources = "\n".join(f"[{s.id}] {s.publisher}: {s.title}\n{s.description}\n{s.url}" for s in topic.sources)
    language_rules = """
For this Hindi script, use Devanagari Hindi throughout every scene. Do not write Hinglish. Translate common
English words instead of leaving them in Latin script; only keep proper names, brand names, and uppercase acronyms.
""" if language == "hi" else ""
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
- Total narration 70-110 words; cut filler rather than repeating the premise.
- Every scene source_ids must refer only to supplied IDs.
- Plan the story as distinct beats: (1) hook with the surprising payoff or stakes, (2) strongest concrete evidence, (3) context or mechanism, (4) who/what is affected, (5) what happens next or what remains unknown, then (6) one-line CTA when using six scenes. Use only beats supported by the sources.
- Every non-CTA scene must introduce one new fact, actor, date, number, contrast, consequence, or unanswered question. The headline, bullets, and narration must support that scene's beat rather than restate another scene.
- Give each scene a visual job as well as a spoken job: the hook should create a pattern interrupt, evidence scenes should show the source or image, bullet scenes should compare or escalate, and the final scene should land the implication. Do not make every scene a headline card.
- Never repeat the topic headline, the same claim, or a sentence pattern across scenes. Do a silent second edit before returning JSON: remove repeated framing, generic transitions, and phrases such as "this is important", "according to the report", and "the big question" unless they carry new information.
- Do not open with "In this video", "Today we are talking about", or background setup. Start with a claim that makes the viewer want the next sentence.
- Instagram CTA should invite following/commenting; YouTube CTA should invite subscribing.
- YouTube metadata is SEO-oriented; Instagram caption is conversational.
{language_rules}
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
