from __future__ import annotations

from .models import ShortScript, Topic


def generate_bilingual(topic: Topic) -> dict[str, ShortScript]:
    """Create both language scripts from one immutable, provenance-bearing topic."""
    source_ids = tuple(source.id for source in topic.sources)
    publisher = topic.sources[0].publisher
    english = f"{topic.headline}. {topic.summary} This report is based on {len(topic.sources)} authenticated source(s), including {publisher}. Follow for the next update."
    hindi = f"हिंदी खबर: {topic.headline}. {topic.summary} यह अपडेट {len(topic.sources)} प्रमाणित स्रोतों पर आधारित है, जिनमें {publisher} भी शामिल है। अगली खबर के लिए फॉलो करें।"
    outputs = {
        "en": ShortScript("en", topic.headline, english, source_ids, topic.approval_status),
        "hi": ShortScript("hi", f"हिंदी: {topic.headline}", hindi, source_ids, topic.approval_status),
    }
    validate_bilingual(outputs, source_ids)
    return outputs


def validate_bilingual(outputs: dict[str, ShortScript], source_ids: tuple[str, ...]) -> None:
    if set(outputs) != {"en", "hi"}:
        raise ValueError("exactly English and Hindi scripts are required")
    for language, script in outputs.items():
        if script.language != language or not script.narration.strip():
            raise ValueError(f"invalid {language} script")
        if script.source_ids != source_ids:
            raise ValueError(f"{language} script evidence does not match the topic")
