import React from 'react';
import {Composition} from 'remotion';
import {NewsShort, newsShortSchema} from './NewsShort';

export const RemotionRoot: React.FC = () => (
  <Composition
    id="NewsShort"
    component={NewsShort}
    durationInFrames={30 * 45}
    fps={30}
    width={1080}
    height={1920}
    schema={newsShortSchema}
    calculateMetadata={({props}) => ({
      durationInFrames: Math.max(30, Math.ceil(props.scenes.reduce((total, scene) => total + (scene.duration || 4), 0) * 30)),
    })}
    defaultProps={{title: 'News update', language: 'en', platform: 'instagram', audio: '', assets: '', bgPreset: 'midnight', font: 'inter', template: 'editorial', scenes: []}}
  />
);
