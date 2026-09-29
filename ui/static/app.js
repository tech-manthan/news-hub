const $ = (s, root = document) => root.querySelector(s);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = {topics: [], selected: null, detail: null, language: 'en', platform: 'instagram'};

async function api(path, options = {}) {
  const response = await fetch(path, {headers: {'Content-Type':'application/json'}, ...options});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || 'Request failed');
  return data;
}
function toast(message, error = false) { const node = $('#toast'); node.textContent = message; node.className = `toast${error ? ' error' : ''}`; node.hidden = false; clearTimeout(window.toastTimer); window.toastTimer = setTimeout(() => {node.hidden = true;}, error ? 6000 : 2800); }
function openModal() { $('#topic-modal').hidden = false; $('#query-input').focus(); }
function closeModal() { $('#topic-modal').hidden = true; $('#modal-error').hidden = true; }
function currentSpec() { return state.detail?.[`spec_${state.language}_${state.platform}`] || null; }

function renderList() {
  $('#topic-count').textContent = state.topics.length;
  $('#topic-list').innerHTML = state.topics.map(topic => `<button class="topic-item ${state.selected === topic.id ? 'selected' : ''}" data-topic="${esc(topic.id)}">
    <h3>${esc(topic.headline)}</h3><div class="topic-meta"><span class="mini-status ${esc(topic.approval_status)}">${topic.approval_status === 'approved' ? 'approved' : 'review'}</span><span>${Number(topic.confidence || 0).toFixed(2)} evidence</span></div>
  </button>`).join('') || '<p class="rail-empty">No coverage yet.</p>';
  document.querySelectorAll('[data-topic]').forEach(item => item.addEventListener('click', () => selectTopic(item.dataset.topic)));
}

function sceneEditor(spec) {
  if (!spec) return `<div class="editor-empty"><strong>No script yet.</strong><span>Write the bilingual draft with Claude, then review every scene here.</span><button class="primary-button" id="write-script">Write script</button></div>`;
  return `<div class="scene-editor" data-spec-language="${spec.language}">${spec.scenes.map((scene, index) => `<article class="scene-row">
    <div class="scene-index">${String(index + 1).padStart(2, '0')}</div><div class="scene-main"><div class="scene-meta"><span>${esc(scene.type.replaceAll('_', ' '))}</span><span>${scene.source_ids.length} sources</span></div>
    <label>Headline<input class="scene-headline" data-scene="${index}" value="${esc(scene.headline)}"></label>
    <label>Voiceover<textarea class="scene-narration" data-scene="${index}" rows="3">${esc(scene.narration)}</textarea></label>
    ${scene.bullets?.length ? `<label>Bullets<textarea class="scene-bullets" data-scene="${index}" rows="2">${esc(scene.bullets.join('\n'))}</textarea></label>` : ''}
    </div></article>`).join('')}</div><div class="editor-footer"><span>Source IDs remain locked to the reviewed evidence.</span><button class="secondary-button" id="save-script">Save script</button><button class="primary-button" id="save-render-script">Save + render</button></div>`;
}

function renderTopic(topic) {
  state.detail = topic; state.selected = topic.id; renderList(); $('#empty-state').hidden = true; $('#topic-view').hidden = false;
  const spec = currentSpec(); const videoName = `short_${state.language}_${state.platform}.mp4`; const hasVideo = topic[`has_video_${state.language}_${state.platform}`];
  const platformLabel = state.platform === 'instagram' ? 'Instagram Reel' : 'YouTube Short';
  const stages = [['script', 'Write'], ['assets', 'Assets'], ['voice', 'Voice'], ['render', 'Render']];
  const stageStatus = topic.stage_status || {};
  $('#topic-view').innerHTML = `<div class="workflow-card"><div class="workflow-heading"><div><div class="eyebrow">PIPELINE CONTROL</div><h2>Build this story</h2></div><div class="workflow-heading-actions"><span class="workflow-note">Each stage can be rerun independently</span><button class="primary-button build-all" id="build-all">Build all <span>→</span></button></div></div><div class="workflow-steps">${stages.map(([stage, label]) => `<button class="workflow-step ${stageStatus[stage] ? 'complete' : ''}" data-stage="${stage}"><span class="step-index">${stageStatus[stage] ? '✓' : '0' + (stages.findIndex(item => item[0] === stage) + 1)}</span><span>${label}</span></button>`).join('')}</div></div><div class="detail-top"><div class="preview-column"><div class="preview-tabs"><button class="preview-tab ${state.platform === 'instagram' ? 'active' : ''}" id="preview-instagram">Instagram cut</button><button class="preview-tab ${state.platform === 'youtube' ? 'active' : ''}" id="preview-youtube">YouTube cut</button></div>${hasVideo ? `<video class="hero-video" src="/media/topics/${encodeURIComponent(topic.id)}/${videoName}?t=${Date.now()}" controls playsinline preload="metadata"></video>` : `<div class="video-empty"><span class="empty-icon">◌</span><strong>Not rendered yet</strong><span>Build voice and render the ${platformLabel.toLowerCase()} from the reviewed script.</span></div>`}<div class="preview-footer"><span class="media-state ${hasVideo ? 'ready' : ''}"><i></i>${hasVideo ? 'Rendered locally' : 'Awaiting render'}</span><span>1080 × 1920 · 9:16</span></div></div>
    <div class="detail-column"><div class="eyebrow">${esc(platformLabel)} / ${esc(topic.approval_status)}</div><h1>${esc(topic.headline)}</h1><p class="detail-summary">${esc(topic.summary)}</p><div class="detail-actions"><button class="primary-button" id="approve-topic" ${topic.approval_status === 'approved' ? 'disabled' : ''}>${topic.approval_status === 'approved' ? 'Approved' : 'Approve topic'} <span>✓</span></button><button class="secondary-button" id="publish-topic" ${topic.approval_status !== 'approved' || !hasVideo ? 'disabled' : ''}>Publish ${state.platform === 'instagram' ? 'Reel' : 'Short'} <span>↗</span></button><button class="secondary-button" id="rewrite-topic">Rewrite</button></div><div class="fact-strip"><div><small>Evidence</small><strong>${Math.round((topic.confidence || 0) * 100)}%</strong></div><div><small>Sources</small><strong>${(topic.sources || []).length}</strong></div><div><small>Language</small><strong>${state.language === 'hi' ? 'हिन्दी' : 'English'}</strong></div></div>
    <div class="metadata-card"><div class="card-heading"><h2>${state.platform === 'instagram' ? 'Instagram caption' : 'YouTube metadata'}</h2><span>${state.platform === 'instagram' ? 'conversational' : 'search-ready'}</span></div>${state.platform === 'instagram' ? `<textarea id="caption-editor" rows="5">${esc(spec?.caption || '')}</textarea>` : `<label>Title<input id="youtube-title" value="${esc(spec?.youtube_title || '')}"></label><label>Description<textarea id="youtube-description" rows="5">${esc(spec?.youtube_description || '')}</textarea></label>`}<div class="metadata-foot"><span>${state.platform === 'instagram' ? `${(spec?.caption || '').length}/2200 characters` : `${(spec?.youtube_description || '').length}/5000 characters`}</span><button class="secondary-button" id="save-metadata">Save metadata</button></div></div></div></div>
    <div class="section-title">Script desk <span class="hint">${spec ? `${spec.scenes.length} scenes · ${spec.scenes.reduce((n, scene) => n + scene.narration.trim().split(/\s+/).length, 0)} words` : 'not written'}</span></div><section class="script-section"><div class="script-toolbar"><div class="script-tabs"><button class="script-tab ${state.language === 'en' ? 'active' : ''}" id="language-en">English</button><button class="script-tab ${state.language === 'hi' ? 'active' : ''}" id="language-hi">हिन्दी</button></div><div class="script-toolbar-right"><span class="voice-status">${topic.has_voice ? '● voice files ready' : '○ voice not built'}</span><button class="secondary-button" id="voice-topic">Build voice</button></div></div>${sceneEditor(spec)}</section>
    <div class="section-title">Evidence ledger <span class="hint">only reviewed sources can enter the script</span></div><div class="source-grid">${(topic.sources || []).map((source, index) => `<article class="source-card"><div class="source-top"><span>${String(index + 1).padStart(2, '0')} · ${esc(source.provider)}</span><span>${esc((source.published_at || '').slice(0, 10))}</span></div><h3>${esc(source.title)}</h3><p>${esc(source.description)}</p><a href="${esc(source.url)}" target="_blank" rel="noopener">Open source <span>↗</span></a></article>`).join('')}</div>`;
  bindTopicActions(topic);
}

function bindTopicActions(topic) {
  $('#preview-instagram').onclick = () => { state.platform = 'instagram'; renderTopic(state.detail); };
  $('#preview-youtube').onclick = () => { state.platform = 'youtube'; renderTopic(state.detail); };
  $('#language-en').onclick = () => { state.language = 'en'; renderTopic(state.detail); };
  $('#language-hi').onclick = () => { state.language = 'hi'; renderTopic(state.detail); };
  $('#approve-topic').onclick = async () => { try { await api(`/api/topics/${encodeURIComponent(topic.id)}/approve`, {method:'POST'}); await selectTopic(topic.id); toast('Topic approved for publishing'); } catch (error) { toast(error.message, true); } };
  $('#publish-topic').onclick = async () => { try { const platform = state.platform; $('#publish-topic').disabled = true; await api(`/api/topics/${encodeURIComponent(topic.id)}/publish/${platform}`, {method:'POST', body: JSON.stringify({language: state.language})}); await selectTopic(topic.id); toast(`${platform === 'instagram' ? 'Instagram Reel' : 'YouTube Short'} published`); } catch (error) { toast(error.message, true); $('#publish-topic').disabled = false; } };
  document.querySelectorAll('[data-stage]').forEach(button => button.onclick = () => runStage(topic, button.dataset.stage));
  $('#build-all').onclick = () => runAllStages(topic);
  $('#write-script')?.addEventListener('click', () => runScript(topic));
  $('#rewrite-topic').onclick = () => runScript(topic);
  $('#voice-topic').onclick = async () => { try { $('#voice-topic').disabled = true; await api(`/api/topics/${encodeURIComponent(topic.id)}/voice`, {method:'POST'}); await selectTopic(topic.id); toast('Voice files generated'); } catch (error) { toast(error.message, true); } };
  $('#render-topic')?.addEventListener('click', () => runStage(topic, 'render'));
  $('#save-metadata').onclick = () => saveCurrentSpec(topic, false);
  $('#save-script')?.addEventListener('click', () => saveCurrentSpec(topic, false));
  $('#save-render-script')?.addEventListener('click', () => saveCurrentSpec(topic, true));
}

async function runStage(topic, stage) { const button = document.querySelector(`[data-stage="${stage}"]`); try { if (button) { button.disabled = true; button.classList.add('running'); } await api(`/api/topics/${encodeURIComponent(topic.id)}/stage`, {method:'POST', body: JSON.stringify({stage})}); await selectTopic(topic.id); toast(`${stage} stage complete`); } catch (error) { toast(error.message, true); } finally { if (button) { button.disabled = false; button.classList.remove('running'); } } }
async function runAllStages(topic) { const button = $('#build-all'); const stages = ['script', 'assets', 'voice', 'render']; try { button.disabled = true; button.innerHTML = 'Building…'; for (const stage of stages) { button.textContent = `${stage}…`; await api(`/api/topics/${encodeURIComponent(topic.id)}/stage`, {method:'POST', body: JSON.stringify({stage})}); } await selectTopic(topic.id); toast('English and Hindi videos are ready'); } catch (error) { toast(error.message, true); } finally { button.disabled = false; button.innerHTML = 'Build all <span>→</span>'; } }

async function runScript(topic) { try { $('#rewrite-topic').disabled = true; await api(`/api/topics/${encodeURIComponent(topic.id)}/script`, {method:'POST'}); await selectTopic(topic.id); toast('English and Hindi scripts are ready'); } catch (error) { toast(error.message, true); } }
async function saveCurrentSpec(topic, renderAfter) {
  const original = currentSpec(); if (!original) return;
  const spec = structuredClone(original); document.querySelectorAll('[data-scene]').forEach(input => { const scene = spec.scenes[Number(input.dataset.scene)]; if (input.classList.contains('scene-headline')) scene.headline = input.value; if (input.classList.contains('scene-narration')) scene.narration = input.value; if (input.classList.contains('scene-bullets')) scene.bullets = input.value.split('\n').map(value => value.trim()).filter(Boolean); });
  if (state.platform === 'instagram') spec.caption = $('#caption-editor')?.value ?? spec.caption; else { spec.youtube_title = $('#youtube-title')?.value ?? spec.youtube_title; spec.youtube_description = $('#youtube-description')?.value ?? spec.youtube_description; }
  try { await api(`/api/topics/${encodeURIComponent(topic.id)}/spec/${state.language}/${state.platform}`, {method:'POST', body: JSON.stringify({spec})}); if (renderAfter) { await api(`/api/topics/${encodeURIComponent(topic.id)}/voice`, {method:'POST'}); await api(`/api/topics/${encodeURIComponent(topic.id)}/render`, {method:'POST'}); } await selectTopic(topic.id); toast(renderAfter ? 'Saved and rendered' : 'Changes saved'); } catch (error) { toast(error.message, true); }
}

async function selectTopic(id) { state.selected = id; try { renderTopic(await api(`/api/topics/${encodeURIComponent(id)}`)); } catch (error) { toast(error.message, true); } }
async function loadTopics(selectId) { state.topics = await api('/api/topics'); renderList(); const target = selectId || state.selected || state.topics[0]?.id; if (target) await selectTopic(target); }
async function fetchTopic() { const button = $('#fetch-topic'); const error = $('#modal-error'); button.disabled = true; error.hidden = true; button.textContent = 'Fetching…'; try { const topic = await api('/api/topics', {method:'POST', body: JSON.stringify({query: $('#query-input').value})}); closeModal(); await loadTopics(topic.id); toast('Fresh coverage is ready'); } catch (err) { error.textContent = err.message; error.hidden = false; } finally { button.disabled = false; button.innerHTML = 'Fetch story <span>→</span>'; } }

$('#new-topic').onclick = openModal; $('#empty-new').onclick = openModal; $('#modal-close').onclick = closeModal; $('#modal-cancel').onclick = closeModal; $('#fetch-topic').onclick = fetchTopic; $('#query-input').onkeydown = event => { if (event.key === 'Enter') fetchTopic(); }; $('#settings-button').onclick = () => toast('Settings are managed in .env and the local setup commands.');
(async function boot() { try { const status = await api('/api/status'); $('#auth-label').textContent = status.authenticated ? `${status.provider} authenticated` : 'public RSS research · no key'; await loadTopics(); } catch (error) { toast(error.message, true); } })();
