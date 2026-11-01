import React from "react";
import { Composition } from "remotion";
import sample from "../../content/s01_silicone-pet-hair-remover/scenes.json";
import { ShortsVideo } from "./ShortsVideo";
import type { ShortsProps } from "./types";
import { theme } from "./theme";

// 기본 props는 첫 번째 콘텐츠. 다른 영상은 --props=../content/<slug>/scenes.json 으로 렌더링한다.
const defaultProps = sample as unknown as ShortsProps;

export const RemotionRoot: React.FC = () => (
  <Composition
    id="ShortsVideo"
    component={ShortsVideo}
    width={theme.width}
    height={theme.height}
    fps={30}
    durationInFrames={300}
    defaultProps={defaultProps}
    calculateMetadata={({ props }) => ({
      fps: props.fps ?? 30,
      durationInFrames: Math.max(
        1,
        props.scenes.reduce((sum, s) => sum + s.durationInFrames, 0),
      ),
    })}
  />
);
