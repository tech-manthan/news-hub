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
  title: z.string(), language: z.string(), platform: z.string().optional(), audio: z.string(), assets: z.string(), scenes: z.array(sceneSchema),
});
type Props = z.infer<typeof newsShortSchema>;
type Scene = Props['scenes'][number];

const COLORS = {
  en: {accent: '#8bf06c', accent2: '#4f9cff'},
  hi: {accent: '#ffb45b', accent2: '#ff6d7d'},
};

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

const SceneView: React.FC<{scene: Scene; assets: string; language: string; index: number}> = ({scene, assets, language, index}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const colors = COLORS[language as 'en' | 'hi'] || COLORS.en;
  const enter = spring({frame, fps, config: {damping: 16, mass: 0.7}});
  const drift = interpolate(frame, [0, 90], [18, 0], {extrapolateRight: 'clamp'});
  const image = scene.asset_id ? `${assets}/${scene.asset_id}.png` : '';
  return <AbsoluteFill style={{background: `radial-gradient(circle at 15% 12%, ${colors.accent2}35 0%, transparent 42%), radial-gradient(circle at 90% 80%, ${colors.accent}22 0%, transparent 45%), #0a0e16`, color: '#f4f7f2', fontFamily: 'Arial, Noto Sans Devanagari, sans-serif', padding: 72}}>
    <div style={{position: 'absolute', top: 0, left: 0, height: 10, width: '100%', background: `linear-gradient(90deg, ${colors.accent}, ${colors.accent2})`}} />
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', opacity: enter}}><div style={{fontSize: 30, letterSpacing: 5, color: colors.accent}}>NEWS ENGINE</div><div style={{fontSize: 22, color: '#aab5c6'}}>{language === 'hi' ? 'हिन्दी' : 'ENGLISH'} · {index + 1}</div></div>
    <div style={{position: 'absolute', top: 245, left: 72, right: 72, opacity: enter, transform: `translateY(${drift}px)`}}>
      <div style={{display: 'inline-block', padding: '10px 16px', border: `1px solid ${colors.accent}88`, borderRadius: 999, color: colors.accent, fontSize: 22, textTransform: 'uppercase', letterSpacing: 2, marginBottom: 34}}>{scene.type.replace(/_/g, ' ')}</div>
      {image ? <div style={{height: 660, borderRadius: 30, overflow: 'hidden', border: '2px solid #ffffff22', background: '#141d2a', boxShadow: '0 30px 80px #0008', marginBottom: 42}}><Img src={staticFile(image)} style={{width: '100%', height: '100%', objectFit: 'cover'}} /></div> : null}
      <div style={{fontSize: image ? 54 : 82, lineHeight: 1.02, letterSpacing: -2, fontWeight: 900, maxWidth: 940}}>{scene.headline}</div>
      {scene.bullets?.length ? <div style={{display: 'grid', gap: 16, marginTop: 38}}>{scene.bullets.map((bullet, bulletIndex) => <div key={bulletIndex} style={{display: 'flex', gap: 18, alignItems: 'center', padding: '17px 20px', background: '#ffffff0d', border: '1px solid #ffffff18', borderRadius: 16, fontSize: 32, fontWeight: 700}}><span style={{display: 'grid', placeItems: 'center', width: 38, height: 38, borderRadius: 12, background: colors.accent, color: '#07100b', fontSize: 22}}>{bulletIndex + 1}</span>{bullet}</div>)}</div> : null}
    </div>
    <div style={{position: 'absolute', bottom: 76, left: 72, right: 72, display: 'flex', justifyContent: 'space-between', color: '#aab5c6', fontSize: 20, letterSpacing: 1}}><span>FACT-CHECKED · REVIEWED SOURCES</span><span>{scene.source_ids?.length || 0} SOURCES</span></div>
    <Captions scene={scene} />
  </AbsoluteFill>;
};

export const NewsShort: React.FC<Props> = ({language, platform, audio, assets, scenes}) => {
  let start = 0;
  return <AbsoluteFill style={{background: '#0a0e16'}}>
    {scenes.map((scene, index) => {
      const from = Math.round(start * 30);
      const duration = Math.max(1, Math.round((scene.duration || 4) * 30));
      start += scene.duration || 4;
      return <Sequence key={`${scene.type}-${index}`} from={from} durationInFrames={duration}><SceneView scene={scene} assets={assets} language={language} index={index} /></Sequence>;
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
