from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

SceneType = Literal["hook_stat", "screenshot_scroll", "image", "bullets", "code_card", "cta"]


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")
    type: SceneType
    narration: str = Field(min_length=1, max_length=420)
    headline: str = Field(min_length=1, max_length=120)
    bullets: list[str] = Field(default_factory=list, max_length=4)
    asset_id: str | None = None
    source_ids: list[str] = Field(default_factory=list, min_length=1)


class LanguageSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")
    language: Literal["en", "hi"]
    title: str = Field(min_length=1, max_length=100)
    scenes: list[Scene] = Field(min_length=5, max_length=7)
    caption: str = Field(min_length=1, max_length=2200)
    hashtags: list[str] = Field(min_length=3, max_length=12)
    youtube_title: str = Field(min_length=1, max_length=100)
    youtube_description: str = Field(min_length=1, max_length=5000)
    youtube_tags: list[str] = Field(min_length=3, max_length=15)
    instagram_cta: str = Field(min_length=1, max_length=160)
    youtube_cta: str = Field(min_length=1, max_length=160)
    source_ids: list[str] = Field(min_length=1)

    @field_validator("hashtags")
    @classmethod
    def hashtags_have_prefix(cls, values: list[str]) -> list[str]:
        if any(not value.startswith("#") for value in values):
            raise ValueError("hashtags must begin with #")
        return values


def validate_spec(spec: LanguageSpec, expected_source_ids: set[str]) -> list[str]:
    errors: list[str] = []
    if set(spec.source_ids) != expected_source_ids:
        errors.append("source_ids must exactly match the research source IDs")
    if spec.scenes[0].type != "hook_stat":
        errors.append("first scene must be hook_stat")
    if spec.scenes[-1].type != "cta":
        errors.append("last scene must be cta")
    if not any(scene.type in ("screenshot_scroll", "image") for scene in spec.scenes[1:-1]):
        errors.append("include at least one evidence visual scene")
    for scene in spec.scenes:
        if set(scene.source_ids) - expected_source_ids:
            errors.append(f"scene {scene.type} references an unknown source ID")
    if spec.language == "hi" and not any("ह" in scene.narration for scene in spec.scenes):
        errors.append("Hindi narration must contain Devanagari text")
    return errors


def platform_variant(spec: LanguageSpec, platform: Literal["instagram", "youtube"]) -> LanguageSpec:
    cta = spec.instagram_cta if platform == "instagram" else spec.youtube_cta
    scenes = [scene.model_copy(deep=True) for scene in spec.scenes]
    scenes[-1].narration = cta
    return spec.model_copy(update={"scenes": scenes})
