import React from 'react';
import {Audio, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig} from 'remotion';
import {z} from 'zod';

export const newsShortSchema = z.object({
  title: z.string(), language: z.string(), audio: z.string(), assets: z.string(),
  scenes: z.array(z.object({type: z.string(), narration: z.string(), headline: z.string(), asset_id: z.string().nullable().optional()})),
});
type Props = z.infer<typeof newsShortSchema>;

export const NewsShort: React.FC<Props> = ({title, language, audio, assets, scenes}) => {
  const frame = useCurrentFrame();
  const {durationInFrames} = useVideoConfig();
  const sceneIndex = Math.min(scenes.length - 1, Math.floor((frame / Math.max(1, durationInFrames)) * Math.max(1, scenes.length)));
  const scene = scenes[sceneIndex] || {headline: title, type: 'hook_stat', narration: ''};
  const opacity = interpolate(frame % 30, [0, 8, 22, 30], [0, 1, 1, 0], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
  const image = scene.asset_id ? `${assets}/${scene.asset_id}.png` : '';
  return <div style={{background: '#101411', color: '#f3f5ee', height: '100%', width: '100%', fontFamily: 'Arial, sans-serif', padding: 72, display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
    {audio ? <Audio src={staticFile(audio)} /> : null}
    <div style={{fontSize: 28, letterSpacing: 5, color: '#b7c7af'}}>NEWS ENGINE · {language.toUpperCase()}</div>
    <div style={{opacity, display: 'flex', flexDirection: 'column', gap: 32}}>
      {image ? <Img src={staticFile(image)} style={{width: '100%', maxHeight: 760, objectFit: 'cover', borderRadius: 28}} /> : null}
      <div style={{fontSize: 76, lineHeight: 1.04, fontWeight: 800}}>{scene.headline}</div>
      <div style={{fontSize: 34, lineHeight: 1.2, color: '#d6ddd2'}}>{scene.narration}</div>
    </div>
    <div style={{fontSize: 24, color: '#91a58a'}}>FACT-CHECKED FROM REVIEWED SOURCES</div>
  </div>;
};
