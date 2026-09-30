# News Engine

Local, human-reviewed news shorts for Instagram Reels and YouTube Shorts. It follows the reel-engine shape: every stage reads and writes files inside `output/<topic-id>/`, so a failed stage can be rerun without rebuilding everything.

Pipeline: `research → script → assets → voice → render → human review → publish`.

For the complete installation and operating process, see [docs/GUIDE.md](docs/GUIDE.md).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,tts,browser,publish]'
cp .env.example .env
brew install ffmpeg
python -m playwright install chromium
python scripts/setup_tts.py
```

## Start the dashboard

Always run these commands from the repository root with the virtual environment active:

```bash
cd /Users/manthansharma/instagram/news-engine
source .venv/bin/activate
NEWS_UI_OPEN=1 python -m ui
```

The dashboard opens at <http://127.0.0.1:8765>. If it does not open automatically, paste that URL into your browser. To start without opening a browser:

```bash
NEWS_UI_OPEN=0 python -m ui
```

Keep this terminal running while using the dashboard. Stop the server with `Ctrl-C`. Change the port with `NEWS_UI_PORT=8791` if 8765 is already occupied.

Before the first start, copy `.env.example` to `.env` and review every variable. The complete variable-by-variable reference is in [docs/GUIDE.md](docs/GUIDE.md).

Piper is the local, open-source TTS backend for both English and Hindi; it needs no TTS API key or cloud call. The bundled setup downloads `en_US-lessac-medium` and `hi_IN-pratham-medium`. See the [Piper CLI documentation](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/CLI.md) and [voice list](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md).

For browser-backed source enrichment and screenshots:

```bash
python -m pip install -e '.[browser]'
python -m playwright install chromium
```

The free research path uses public Google News RSS. If `NEWSAPI_KEY` is configured, the adapter uses NewsAPI instead. Browser work is restricted to the configured Google News allowlist; it does not bypass logins, paywalls, or robots restrictions. Claude is invoked through the local `claude -p` CLI, so no Anthropic API key is placed in this project.

## Build a topic

```bash
python run.py --query "AI policy" --stages research
python run.py --query "AI policy" --stages script,assets,voice,render
```

The first command writes `research.json`. The full run creates:

- `spec_{en,hi}_{instagram,youtube}.json` — validated scene specs and platform metadata
- `assets/` and `assets.json` — source screenshots and provenance
- `voice/{language}/{platform}/scene_*.wav` and `voice_{language}_{platform}.json`
- `audio_{language}_{platform}.wav` and `short_{language}_{platform}.mp4`

The script stage makes one structured `claude -p` call per language, retries once with validation errors, and uses the same evidence IDs for both languages. Instagram and YouTube receive distinct spoken CTAs and metadata.

Resume an existing topic:

```bash
python run.py --dir output/<topic-id> --stages voice,render
python run.py --query "technology" --dry-run
```

Install `ffmpeg` before rendering. The current renderer is a dependable local 9:16 fallback; the artifact contract is ready for a Remotion composition when the Node renderer is installed.

To use the Remotion composition instead of the FFmpeg fallback:

```bash
cd render && npm install && cd ..
REMOTION_RENDER=1 python run.py --dir output/<topic-id> --stages render
```

Remotion composes the scene cards, source image, narration audio, and language treatment from the same per-topic props contract. FFmpeg remains the fallback for machines that do not have Node dependencies installed.

## Dashboard

```bash
NEWS_UI_OPEN=1 python -m ui
```

Open <http://127.0.0.1:8765>. The dashboard provides source evidence, a four-video gallery, bilingual script review, selectable Piper voices with preview, language/platform selection, a one-click **Build all** action (script → assets → voice → render), individual stage reruns, a trending automation loop, video preview, approval state, settings, and manual publish actions. Nothing is posted without an explicit approval and publish click.

To schedule local builds with macOS’ native scheduler (still never publishing automatically):

```bash
python schedule.py --query "technology" --hour 9 --minute 0
launchctl load data/com.newsengine.build.plist
```

## Publishing

Publishing uses official platform APIs only and is optional:

```bash
python publish.py --instagram-setup
python publish.py --youtube-setup
python publish.py --check
python publish.py output/<topic-id> --language en --instagram --yes
python publish.py output/<topic-id> --language hi --youtube --yes
```

Instagram requires an eligible professional account and Meta credentials. YouTube requires OAuth client JSON at `data/youtube_client_secret.json`. Publish records are written per platform and language to prevent duplicate posts.

Optional fixed-keyword comment replies are explicit and deterministic:

```bash
python reply.py --instagram-media-id <id>
python reply.py --youtube-video-id <id> --yes
```

The default is preview-only. Use `--yes` to send replies; only comments containing `AUTO_REPLY_KEYWORD` are selected, and replied IDs are persisted to prevent repeats.

## Tests

```bash
python -m unittest discover -s tests -v
python -m compileall -q run.py news_engine ui
```
