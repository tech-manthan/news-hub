# News Engine

This project turns a fresh, authenticated news topic into two short-script artifacts: English and Hindi. It follows the reference reel engine’s staged model, but adds news-specific safeguards: provider authentication, HTTPS/domain filtering, freshness windows, deduplication, source diversity scoring, provenance, and a human approval gate.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
cp .env.example .env
```

Set `NEWSAPI_KEY` in `.env`. The engine only uses the configured provider API; it does not scrape arbitrary websites. Keep credentials and service-account JSON outside Git. Hindi TTS is available through `GoogleHindiTTS` when `google-cloud-texttospeech` and `GOOGLE_APPLICATION_CREDENTIALS` are configured. English TTS uses the same local Kokoro approach as the reference engine through `KokoroEnglishTTS`.

## Generate a topic

```bash
export NEWSAPI_KEY='...'
python run.py --query "technology"
```

This writes `output/<topic-id>/research.json`, `spec_en.json`, and `spec_hi.json`. Both specs contain the same `source_ids`. `--approve` records human approval for the fetched topic; publishing code should call `require_approved` immediately before posting.

## Tests

```bash
python -m unittest discover -v
```

The current slice intentionally stops at auditable research, bilingual scripts, and TTS artifact contracts. Remotion rendering, Instagram/YouTube publishing, scheduled jobs, and performance analytics should consume these artifacts in the next slices.
