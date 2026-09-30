# News Engine: complete operating guide

This guide is the handoff for running the local news-short factory. It covers installation, source verification, bilingual generation, human review, rendering, and optional manual publishing.

## What the application does

For every topic, the engine creates four publishable variants:

| Language | Instagram | YouTube |
|---|---|---|
| English | Reel with a short social CTA | Short with an SEO-oriented title and subscribe CTA |
| Hindi | Reel with a short social CTA | Short with an SEO-oriented title and subscribe CTA |

Each topic is isolated in `output/<topic-id>/`. Stages are restartable:

`research → script → assets → voice → render → review → publish`

The application is human-in-the-loop. Building files is automated; publishing requires an explicit approval and publish action in the dashboard or CLI.

## 1. Install on macOS

```bash
cd /Users/manthansharma/instagram/news-engine
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test,tts,browser,publish]'
cp .env.example .env
brew install ffmpeg
python -m playwright install chromium
```

Claude is used through the local Claude Code CLI, not an API key:

```bash
claude --version
claude login
```

Confirm that the command works before running the script stage. The engine uses the model configured by `SCRIPT_MODEL` (the default is `opus`).

## 2. Configure `.env`

Start from `.env.example`. The important settings are:

```dotenv
NEWS_QUERY=technology
NEWS_MAX_AGE_HOURS=48
NEWS_MINIMUM_SOURCES=1
SCRIPT_MODEL=opus
PUBLIC_RESEARCH=1
PUBLIC_RESEARCH_BROWSER=0
ENGLISH_TTS_MODEL=data/voices/en_US-lessac-medium.onnx
HINDI_TTS_MODEL=data/voices/hi_IN-pratham-medium.onnx
ENGLISH_TTS_BACKEND=kokoro
HINDI_TTS_BACKEND=piper
KOKORO_PYTHON=
TTS_MODEL_DIR=data/voices
```

The default research path is free Google News RSS. `NEWSAPI_KEY` is optional; leave it empty to avoid a paid news API. Public research accepts only the configured/allowlisted sources and records source URLs, titles, timestamps, and evidence IDs in `research.json`. Browser enrichment is optional and does not bypass logins, paywalls, robots restrictions, or access controls.

### Environment variable reference

| Variable | Required? | Purpose |
|---|---|---|
| `NEWSAPI_KEY` | No | Optional NewsAPI credential. Blank uses free Google News RSS. |
| `NEWS_QUERY` | No | Default topic for CLI/scheduled runs; defaults to `technology`. |
| `NEWS_LANGUAGE` | No | Research language; defaults to `en`. |
| `NEWS_MAX_AGE_HOURS` | No | Freshness window; defaults to `48`. |
| `NEWS_MINIMUM_SOURCES` | No | Minimum source count for CLI selection. |
| `SCRIPT_MODEL` | No | Model passed to the local `claude -p` command; defaults to `opus`. |
| `PUBLIC_RESEARCH` | No | Public research feature flag; keep `1` for the default path. |
| `PUBLIC_RESEARCH_BROWSER` | No | Set `1` to enable Playwright enrichment/screenshots; otherwise `0`. |
| `TTS_MODEL_DIR` | No | Directory containing Piper models. |
| `ENGLISH_TTS_MODEL` | No | Documented English model path; the voice stage uses the matching file in `TTS_MODEL_DIR`. |
| `HINDI_TTS_MODEL` | No | Documented Hindi model path; the voice stage uses the matching file in `TTS_MODEL_DIR`. |
| `ENGLISH_TTS_VOICE` | No | Selected English Piper `.onnx` filename; can also be changed in dashboard Settings. |
| `HINDI_TTS_VOICE` | No | Selected Hindi Piper `.onnx` filename; can also be changed in dashboard Settings. |
| `ENGLISH_TTS_BACKEND` | No | `kokoro` by default; `piper` is also available for English. |
| `HINDI_TTS_BACKEND` | No | `piper` by default; Kokoro is currently English-only. |
| `KOKORO_PYTHON` | No | Optional path to the reel-engine Python environment; auto-detects `../reel-engine/.venv/bin/python`. |
| `REMOTION_RENDER` | No | Set `1` to use the installed Remotion renderer; `0` uses FFmpeg. |
| `NEWS_UI_PORT` | No | Local dashboard port; defaults to `8765`. |
| `NEWS_UI_OPEN` | No | Set `1` to open a browser on startup; set `0` for headless startup. |
| `META_USER_TOKEN` | Publishing only | Meta Graph API user token for Instagram setup. |
| `META_API_VERSION` | Publishing only | Meta Graph API version; defaults to `v26.0`. |
| `AUTO_REPLY_KEYWORD` | Reply tool only | Fixed substring the reply bot looks for. |
| `AUTO_REPLY_TEXT` | Reply tool only | Fixed response sent to matching comments. |
| `AUTO_REPLY_STATE` | Reply tool only | Local file used to prevent duplicate replies. |

There are two files that are intentionally not environment variables: `data/youtube_client_secret.json` is the Google OAuth desktop client, and `data/yt_token.json` is generated after consent. Both stay local and must never be committed.

## 3. Start the dashboard

Run from the repository root, after activating the virtual environment and creating `.env`:

```bash
cd /Users/manthansharma/instagram/news-engine
source .venv/bin/activate
NEWS_UI_OPEN=1 python -m ui
```

Open <http://127.0.0.1:8765>. The server binds to localhost only. `NEWS_UI_OPEN=1` opens the browser automatically; use `NEWS_UI_OPEN=0` when starting from a terminal, script, or remote session. If the port is busy:

```bash
NEWS_UI_PORT=8791 NEWS_UI_OPEN=0 python -m ui
```

Stop the server with `Ctrl-C`. Do not close the terminal while you are using the dashboard. The UI is the control center: select a topic, fetch research, run Write/Assets/Voice/Render, review both languages and platforms, approve, and publish.

If startup fails, run `python -m ui` from the repository root—not from inside `ui/`—and verify `.venv/bin/python` and `.env` exist.

## 4. Install the free local voices

Piper is the open-source local TTS backend. It runs on the Mac and does not call a paid speech service.

```bash
source .venv/bin/activate
python scripts/setup_tts.py
```

Expected files include:

```text
data/voices/en_US-lessac-medium.onnx
data/voices/en_US-lessac-medium.onnx.json
data/voices/hi_IN-pratham-medium.onnx
data/voices/hi_IN-pratham-medium.onnx.json
```

The voice stage writes one WAV per scene and word-level timing metadata, so captions do not need a second transcription service.

To add another local Piper voice from the dashboard, open **Settings → Voices**, enter its official id (for example `en_US-amy-medium`), and click **Install voice**. The model and its `.onnx.json` configuration are downloaded into `TTS_MODEL_DIR`; the new model then appears in both voice selectors. The same panel includes independent English/Hindi backend selectors, speed controls, and voice previews. Piper’s supported voice ids are documented in its [official voice list](https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md).

Kokoro does not download a second model for News Engine. It invokes the existing Kokoro package from reel-engine and reuses its local Hugging Face cache. The dashboard exposes Kokoro's downloaded voice catalog; choose any voice and build English audio. If reel-engine is elsewhere, set `KOKORO_PYTHON` to its `.venv/bin/python` path. Kokoro word timings are written into the scene manifest and drive captions directly.

## 5. Generate a topic

Research only:

```bash
python run.py --query "AI policy" --stages research
```

Run every stage:

```bash
python run.py --query "AI policy"
```

Run selected stages or resume a failed topic:

```bash
python run.py --dir output/<topic-id> --stages script,assets,voice,render
python run.py --dir output/<topic-id> --stages voice,render
python run.py --query "technology" --dry-run
```

The output folder contains:

```text
research.json                         verified source ledger and evidence
spec_en_instagram.json                validated English Reel spec
spec_hi_youtube.json                  validated Hindi YouTube spec
assets/                               screenshots and downloaded media
assets.json                           asset provenance
voice/<language>/<platform>/          per-scene WAV files
voice_<language>_<platform>.json      timing and voice metadata
short_<language>_<platform>.mp4       final video variants
```

The script call is structured and Pydantic-validated. If Claude returns invalid JSON, the engine retries once with the validation errors. Scene types include `hook_stat`, `screenshot_scroll`, `image`, `bullets`, `code_card`, and `cta`. Every factual scene must refer to evidence from `research.json`.

## 6. Use the dashboard

```bash
NEWS_UI_OPEN=1 python -m ui
```

Open <http://127.0.0.1:8765>.

Recommended review flow:

1. Create or fetch a topic.
2. Inspect the source ledger and open the source links.
3. Generate or rewrite the English and Hindi scripts.
4. Switch between Instagram and YouTube variants.
5. Edit narration, scene text, captions, title, description, and tags inline.
6. Save the metadata and script.
7. Click **Build all** to run script → assets → voice → render in order, or run one stage independently when iterating.
8. Watch the MP4 and verify the hook, facts, pronunciation, captions, and final CTA.
9. Mark the item approved.
10. Click publish only after approval.

The dashboard stores saved settings with higher precedence than `.env`, followed by code defaults. No scheduler or build command publishes by itself.

The left rail’s **Trending loop** can repeatedly fetch the configured beat, capture source visuals, generate both scripts, synthesize both voices, and render all four outputs. It stops at the review queue; it never approves or publishes. The top-right Settings button opens the local workspace configuration drawer for query, freshness, browser capture, voice selection/speed, renderer, and appearance. **Video look** controls the template (`Editorial`, `Bulletin`, `Minimal`), background (`Midnight`, `Sunset`, `Forest`, `Mono dark`), and typeface. Save settings before rerendering. To remove a story, open it and click **Delete topic**; this removes its local output folder and database record, while the demo topic is intentionally protected.

Hindi copy is required to be Devanagari-first. Proper names, brands, and uppercase acronyms such as AI or Google may remain in Latin script; ordinary words such as “tech”, “runaway”, or “subscribe” are rejected by validation and sent back to Claude for correction.

## 7. Remotion and FFmpeg

FFmpeg is the dependable fallback renderer and is used when the Node/Remotion stack is not installed. Remotion is the scene composition layer for the richer template path; it does not replace FFmpeg for audio encoding, muxing, or final platform-compatible re-encoding.

Install and use Remotion:

```bash
cd render
npm install
npx remotion browser ensure
cd ..
REMOTION_RENDER=1 python run.py --dir output/<topic-id> --stages render
```

Both renderers consume the same props contract produced from the validated spec, assets, and voice timings. If Remotion fails, remove `REMOTION_RENDER=1` and rerun the render stage with FFmpeg.

## 7. YouTube connection

1. Create a project in Google Cloud Console.
2. Enable **YouTube Data API v3**.
3. Configure the OAuth consent screen. For a personal app, External is fine; add the Google account that owns the channel as a test user while the app is in Testing.
4. Create an OAuth client of type **Desktop app**.
5. Download the JSON and save it as `data/youtube_client_secret.json`.
6. Run:

```bash
python publish.py --youtube-setup
python publish.py --youtube-check
```

Complete the browser consent once. The refresh token is saved locally as `data/yt_token.json` and is ignored by Git. During OAuth Testing, Google can expire refresh tokens after seven days; moving the consent screen to In production avoids that testing limitation for a personal app, subject to Google policy.

Official references: [YouTube installed-app OAuth](https://developers.google.com/youtube/v3/guides/auth/installed-apps) and [Google OAuth testing status](https://support.google.com/cloud/answer/15549945?hl=en).

## 8. Instagram / Facebook Page connection

The current publisher uses the official Graph API Facebook Login flow: Facebook user token → Page access token → linked Instagram professional account. It is not an Instagram-password automation flow.

### Prepare the accounts

1. Convert Instagram to a Business or Creator account.
2. Create or select a Facebook Page and link the Instagram professional account to it.
3. In Meta Business Suite, ensure your user has full control of the Page and business assets.
4. Create a Meta app and add the Facebook Login / Instagram Graph API products.
5. Add your account as an app role or tester while the app is in development mode.

### Create the user token

Use [Graph API Explorer](https://developers.facebook.com/tools/explorer/):

1. Select the News Hub app in the app dropdown.
2. Keep the host as `graph.facebook.com`.
3. Choose **Get User Access Token**.
4. Add the permissions needed by the publisher: `pages_show_list`, `pages_read_engagement`, `instagram_basic`, and `instagram_content_publish`.
5. Add comment permissions only if you use the optional fixed-keyword reply tool.
6. Generate the token and copy it into `.env`:

```dotenv
META_USER_TOKEN=your-user-token
```

Then validate the Page and Instagram link:

```bash
python publish.py --instagram-setup
python publish.py --instagram-check
```

If the Page does not appear, check that the logged-in Facebook user has Page access, the Page is linked to the Instagram professional account, the correct Meta app is selected in Explorer, and the requested permissions were granted. Do not paste tokens into chat, GitHub, screenshots, or issue reports.

Useful Meta references: [Page access](https://www.facebook.com/help/289207354498410/r.php/), [give and edit Page access](https://www.facebook.com/help/187316341316631), and Meta's [Instagram API with Facebook Login collection](https://www.postman.com/meta/instagram/folder/9cgqucg/instagram-api-with-facebook-login).

## 9. Approve and publish

CLI publishing is intentionally gated:

```bash
python publish.py --platform instagram --language en --dir output/<topic-id> --approve
python publish.py --platform youtube --language hi --dir output/<topic-id> --approve
```

Use the dashboard for the safer workflow: review → approve → publish. Instagram publishing requires a publicly reachable media URL during the container upload step; configure the local/public media setting documented by the publisher before using it outside development. YouTube uploads are sent through the authenticated official API.

## 10. Local scheduling

Scheduling builds content; it does not publish content.

```bash
python schedule.py --query "technology" --hour 9 --minute 0
launchctl load data/com.newsengine.build.plist
```

Unload it when needed:

```bash
launchctl unload data/com.newsengine.build.plist
```

Review generated items in the dashboard and publish manually after approval.

## 11. Fixed-keyword replies

Configure a deterministic keyword and template in `.env`:

```dotenv
AUTO_REPLY_KEYWORD=link
AUTO_REPLY_TEXT=Here is the link: https://example.com
AUTO_REPLY_STATE=data/reply_state.json
```

Run replies only for your own published media:

```bash
python reply.py --instagram-media-id <id>
python reply.py --youtube-video-id <id> --yes
```

The matcher is a fixed substring check and the reply is a fixed template. It never invents a keyword or generates a new reply for each comment.

## 12. Troubleshooting

**`claude: command not found`** — install/login to Claude Code and make sure the shell running `.venv` can see the `claude` executable.

**Voice stage says a model is missing** — rerun `python scripts/setup_tts.py`, then check the two `.onnx` paths in `.env`.

**Browser screenshots fail** — run `python -m playwright install chromium` and keep `PUBLIC_RESEARCH_BROWSER=0` until the browser path is needed.

**Remotion fails** — run `cd render && npm install && npx remotion browser ensure`; otherwise rerun with the FFmpeg fallback.

**Instagram Page is missing** — verify Page access, Page-to-Instagram linking, app selection, permissions, and that `META_USER_TOKEN` is the newly generated token.

**YouTube access denied** — confirm the YouTube API is enabled, the channel account is an OAuth test user, and rerun `python publish.py --youtube-setup` after deleting only the stale `data/yt_token.json` if re-consent is required.

## 13. Verify the checkout

```bash
source .venv/bin/activate
python -m unittest discover -s tests -q
git diff --check
git status --short
```

Keep `.env`, OAuth client secrets, refresh tokens, access tokens, generated media, and downloaded voice models out of Git. The repository ignore rules already cover the runtime data paths; check `git status` before every commit.
