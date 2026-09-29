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
    defaultProps={{title: 'News update', language: 'en', audio: '', assets: '', scenes: []}}
  />
);
