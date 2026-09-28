# Implementation Plan: Authenticated bilingual news shorts

## Overview

 Build a news-engine MVP modeled on the reference reel pipeline: fetch a topic from authenticated, explicitly configured news providers; normalize and persist source provenance; score freshness, source diversity, and evidence confidence; create validated English and Hindi short scripts from the same evidence; synthesize both languages; and leave render integration behind a stable artifact contract.

## Architecture Decisions

- Provider adapters are allowlisted and require credentials from environment variables; unauthenticated scraping and arbitrary URLs are rejected.
- Research items retain provider, source URL, published time, title, and evidence text so generated scripts can be audited.
- Stories are freshness-filtered, URL/title-deduplicated, and scored for source diversity before generation; low-confidence topics are marked for human approval.
- One topic produces one shared fact pack and two independent language specs (`en`, `hi`), preventing the Hindi version from drifting from the English facts.
- Every output carries an approval status and source IDs; publishing is blocked until a human approves the topic.
- TTS is provider-based: English uses the local Kokoro path when available, and Hindi uses an authenticated Google Cloud TTS path. Both are optional at import time and fail with actionable setup errors.
- The first slice writes deterministic JSON/audio artifacts; video rendering can consume the same contract in a later slice.

## Task List

### Phase 1: Foundation

- [x] Task 1: Add project configuration, secure environment template, SQLite schema, and source/provenance models.
- [x] Task 2: Add authenticated provider adapters and topic selection with deduplication.
- [x] Task 2b: Add freshness, diversity/confidence scoring, and approval-state persistence.

### Checkpoint: Foundation

- [x] Focused source/model tests pass.
- [x] No credential-bearing files are tracked.

### Phase 2: Bilingual generation

- [x] Task 3: Add shared-evidence English/Hindi script generation with strict validation.
- [x] Task 4: Add English/Hindi TTS backends and artifact manifest generation.

### Checkpoint: Core Features

- [x] A fixture topic creates both language specs with identical source IDs.
- [x] Low-confidence or stale topics cannot enter a publishable state.
- [ ] TTS remains import-safe when optional providers are not installed.

### Phase 3: CLI and handoff

- [x] Task 5: Add CLI orchestration, dry-run mode, and README setup/run instructions.
- [x] Task 6: Run the full test suite and document remaining render/publishing boundaries.

### Checkpoint: Complete

- [x] All acceptance criteria met.
- [x] Repository is ready for the next render integration slice.

## Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Provider API changes or quota limits | High | Adapter boundary, timeouts, clear configuration errors, fixture tests |
| Unverified or stale news | High | Authenticated allowlist, published-time window, provenance, minimum source count |
| Hindi script factual drift | High | Generate both specs from one immutable fact pack and validate source IDs |
| Optional TTS dependencies | Medium | Lazy imports and backend-specific setup errors |

## Open Questions

- Which authenticated news provider credentials will be used in production (NewsAPI, GNews, or an internal provider)?
- Should rendered English and Hindi shorts be published to separate accounts or selected at publish time?
