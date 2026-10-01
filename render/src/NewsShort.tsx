import React from 'react';
import {AbsoluteFill, Audio, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';

const wordSchema = z.object({text: z.string(), start: z.number(), end: z.number()});
const sceneSchema = z.object({
  type: z.string(), narration: z.string(), headline: z.string(), bullets: z.array(z.string()).optional(),
  asset_id: z.string().nullable().optional(), source_ids: z.array(z.string()).optional(),
  duration: z.number().optional(), words: z.array(wordSchema).optional(),
});
export const newsShortSchema = z.object({
  title: z.string(), language: z.string(), platform: z.string().optional(), audio: z.string(), assets: z.string(), bgPreset: z.string().optional(), font: z.string().optional(), template: z.string().optional(), scenes: z.array(sceneSchema),
});
type Props = z.infer<typeof newsShortSchema>;
type Scene = Props['scenes'][number];

const COLORS = {
  en: {accent: '#8bf06c', accent2: '#4f9cff'},
  hi: {accent: '#ffb45b', accent2: '#ff6d7d'},
};
const BACKGROUNDS: Record<string, string> = {midnight: '#0a0e16', sunset: '#24151c', forest: '#0d1c18', mono_dark: '#111313'};
const FONTS: Record<string, string> = {inter: 'Arial, sans-serif', poppins: 'Trebuchet MS, Arial, sans-serif', space_grotesk: 'Arial, sans-serif', plex_sans: 'Arial, Noto Sans Devanagari, sans-serif'};

const Captions: React.FC<{scene: Scene}> = ({scene}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const t = frame / fps;
  const words = scene.words || [];
  if (!words.length) return null;
  const active = Math.max(0, words.findIndex((word, index) => t >= word.start && t < (words[index + 1]?.start ?? word.end + 0.35)));
  const page = words.slice(Math.max(0, active - 1), Math.max(0, active - 1) + 4);
  return <div style={{position: 'absolute', left: 70, right: 70, bottom: 255, display: 'flex', justifyContent: 'center', flexWrap: 'wrap', gap: '0 18px', textAlign: 'center'}}>
    {page.map((word, index) => <span key={`${word.text}-${index}`} style={{fontSize: 58, lineHeight: 1.08, fontWeight: 900, color: index === 1 ? '#ffe36a' : '#fff', textShadow: '0 4px 14px #000, 0 0 3px #000', WebkitTextStroke: '2px rgba(0,0,0,.7)', paintOrder: 'stroke fill'}}>{word.text}</span>)}
  </div>;
};

const SceneView: React.FC<{scene: Scene; assets: string; language: string; platform?: string; index: number; bgPreset?: string; font?: string; template?: string}> = ({scene, assets, language, platform, index, bgPreset, font, template}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const colors = COLORS[language as 'en' | 'hi'] || COLORS.en;
  const enter = spring({frame, fps, config: {damping: 15, mass: 0.65}});
  const settle = spring({frame: Math.max(0, frame - 7), fps, config: {damping: 18, mass: 0.7}});
  const drift = interpolate(frame, [0, 120], [26, 0], {extrapolateRight: 'clamp'});
  const imageScale = interpolate(frame, [0, 150], [1.08, 1], {extrapolateRight: 'clamp'});
  const image = scene.asset_id ? `${assets}/${scene.asset_id}.png` : '';
  const base = BACKGROUNDS[bgPreset || 'midnight'] || BACKGROUNDS.midnight;
  const flat = template === 'minimal';
  const isHook = scene.type === 'hook_stat';
  const isCta = scene.type === 'cta';
  const isBullets = scene.type === 'bullets';
  const hasImage = Boolean(image) && !isHook && !isCta;
  const sceneLabel = isHook ? 'THE STORY' : isCta ? 'THE TAKEAWAY' : scene.type === 'screenshot_scroll' ? 'SOURCE CHECK' : scene.type === 'image' ? 'LOOK CLOSER' : scene.type.replace(/_/g, ' ');
  const ctaWord = platform === 'youtube' ? 'SUBSCRIBE FOR THE NEXT UPDATE' : 'FOLLOW FOR THE NEXT UPDATE';
  return <AbsoluteFill style={{background: flat ? base : `radial-gradient(circle at 15% 12%, ${colors.accent2}35 0%, transparent 42%), radial-gradient(circle at 90% 80%, ${colors.accent}22 0%, transparent 45%), ${base}`, color: '#f4f7f2', fontFamily: FONTS[font || 'inter'] || FONTS.inter, padding: 72}}>
    <div style={{position: 'absolute', top: 0, left: 0, height: 12, width: '100%', background: `linear-gradient(90deg, ${colors.accent}, ${colors.accent2})`}} />
    <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', opacity: enter}}><div style={{display: 'flex', alignItems: 'center', gap: 14}}><span style={{width: 13, height: 13, borderRadius: 99, background: colors.accent, boxShadow: `0 0 0 8px ${colors.accent}18`}} /><div style={{fontSize: 27, letterSpacing: 4, fontWeight: 800, color: colors.accent}}>NEWS ENGINE</div></div><div style={{fontSize: 20, color: '#aab5c6', fontWeight: 700}}>{String(index + 1).padStart(2, '0')}</div></div>
    {isHook ? <div style={{position: 'absolute', top: 255, left: 72, right: 72, opacity: enter, transform: `translateY(${drift}px)`}}><div style={{display: 'inline-flex', alignItems: 'center', gap: 12, color: colors.accent, fontSize: 21, fontWeight: 800, letterSpacing: 3}}><span style={{width: 42, height: 4, background: colors.accent}} />{sceneLabel}</div><div style={{marginTop: 30, fontSize: 88, lineHeight: .98, letterSpacing: -3, fontWeight: 900, maxWidth: 930}}>{scene.headline}</div><div style={{position: 'absolute', top: -30, right: -10, fontSize: 230, lineHeight: 1, color: `${colors.accent}12`, fontWeight: 900}}>!</div></div> : null}
    {hasImage ? <div style={{position: 'absolute', top: 185, left: 72, right: 72, opacity: enter, transform: `translateY(${drift}px)`}}><div style={{display: 'flex', alignItems: 'center', gap: 12, color: colors.accent, fontSize: 20, fontWeight: 800, letterSpacing: 2, marginBottom: 22}}><span style={{width: 10, height: 10, borderRadius: 99, background: colors.accent}} />{sceneLabel}</div><div style={{height: 630, borderRadius: 28, overflow: 'hidden', border: `2px solid ${colors.accent}66`, background: '#141d2a', boxShadow: '0 30px 80px #0009', position: 'relative'}}><Img src={staticFile(image)} style={{width: '100%', height: '100%', objectFit: 'cover', transform: `scale(${imageScale})`}} /><div style={{position: 'absolute', inset: 0, background: `linear-gradient(180deg, #00000008 30%, ${base}f5 100%)`}} /></div><div style={{position: 'absolute', left: 28, right: 28, bottom: 26, fontSize: 49, lineHeight: 1.04, letterSpacing: -1.5, fontWeight: 900}}>{scene.headline}</div></div> : null}
    {isBullets ? <div style={{position: 'absolute', top: 230, left: 72, right: 72, opacity: enter, transform: `translateY(${drift}px)`}}><div style={{color: colors.accent, fontSize: 20, fontWeight: 800, letterSpacing: 2, marginBottom: 24}}>{sceneLabel}</div><div style={{fontSize: 59, lineHeight: 1.02, letterSpacing: -2, fontWeight: 900, maxWidth: 920, marginBottom: 42}}>{scene.headline}</div><div style={{display: 'grid', gap: 17}}>{(scene.bullets || []).map((bullet, bulletIndex) => { const cardIn = spring({frame: Math.max(0, frame - bulletIndex * 7), fps, config: {damping: 17, mass: .7}}); return <div key={bulletIndex} style={{display: 'flex', gap: 18, alignItems: 'center', padding: '18px 20px', background: '#ffffff0d', border: `1px solid ${colors.accent}44`, borderRadius: 16, fontSize: 31, fontWeight: 700, opacity: cardIn, transform: `translateX(${(1 - cardIn) * 38}px)`}}><span style={{display: 'grid', placeItems: 'center', flex: '0 0 auto', width: 42, height: 42, borderRadius: 12, background: colors.accent, color: '#07100b', fontSize: 22}}>{bulletIndex + 1}</span><span>{bullet}</span></div>; })}</div></div> : null}
    {isCta ? <div style={{position: 'absolute', top: 355, left: 72, right: 72, textAlign: 'center', opacity: settle, transform: `translateY(${(1 - settle) * 24}px)`}}><div style={{display: 'inline-block', color: colors.accent, fontSize: 20, fontWeight: 800, letterSpacing: 3, marginBottom: 30}}>{sceneLabel}</div><div style={{fontSize: 72, lineHeight: 1, letterSpacing: -2, fontWeight: 900}}>{scene.headline}</div><div style={{display: 'inline-block', marginTop: 46, padding: '17px 25px', borderRadius: 999, background: colors.accent, color: '#07100b', fontSize: 23, fontWeight: 900, letterSpacing: 1}}>{ctaWord}</div></div> : null}
    {!isHook && !hasImage && !isBullets && !isCta ? <div style={{position: 'absolute', top: 290, left: 72, right: 72, opacity: enter, transform: `translateY(${drift}px)`}}><div style={{color: colors.accent, fontSize: 20, fontWeight: 800, letterSpacing: 2, marginBottom: 28}}>{sceneLabel}</div><div style={{fontSize: 68, lineHeight: 1, letterSpacing: -2, fontWeight: 900, maxWidth: 930}}>{scene.headline}</div></div> : null}
    <div style={{position: 'absolute', bottom: 76, left: 72, right: 72, display: 'flex', justifyContent: 'space-between', color: '#aab5c6', fontSize: 18, fontWeight: 700, letterSpacing: 1}}><span>VERIFIED SOURCES</span><span>{scene.source_ids?.length || 0} SOURCES</span></div>
    <Captions scene={scene} />
  </AbsoluteFill>;
};

export const NewsShort: React.FC<Props> = ({language, platform, audio, assets, scenes, bgPreset, font, template}) => {
  let start = 0;
  return <AbsoluteFill style={{background: '#0a0e16'}}>
    {scenes.map((scene, index) => {
      const from = Math.round(start * 30);
      const duration = Math.max(1, Math.round((scene.duration || 4) * 30));
      start += scene.duration || 4;
      return <Sequence key={`${scene.type}-${index}`} from={from} durationInFrames={duration}><SceneView scene={scene} assets={assets} language={language} platform={platform} index={index} bgPreset={bgPreset} font={font} template={template} /></Sequence>;
    })}
    {audio ? <Audio src={staticFile(audio)} /> : null}
    <div style={{position: 'absolute', bottom: 0, left: 0, height: 8, width: '100%', background: '#ffffff1c'}}><Progress /></div>
  </AbsoluteFill>;
};

const Progress: React.FC = () => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  return <div style={{height: '100%', width: `${Math.min(100, (frame / Math.max(1, durationInFrames)) * 100)}%`, background: 'linear-gradient(90deg, #8bf06c, #4f9cff)'}} />;
};
