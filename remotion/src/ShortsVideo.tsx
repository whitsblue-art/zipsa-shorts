import React from "react";
import { AbsoluteFill, Audio, Series, staticFile } from "remotion";
import { ProgressBar } from "./components/Stage";
import { CoverScene } from "./scenes/CoverScene";
import { CtaScene } from "./scenes/CtaScene";
import { PointScene } from "./scenes/PointScene";
import { ProblemScene } from "./scenes/ProblemScene";
import { ProductScene } from "./scenes/ProductScene";
import type { Scene, ShortsProps } from "./types";

/** 씬 type → 컴포넌트. 새 씬을 만들면 여기와 types.ts에 추가한다. */
const SCENES: { [K in Scene["type"]]: React.FC<Extract<Scene, { type: K }>> } = {
  cover: CoverScene,
  problem: ProblemScene,
  product: ProductScene,
  point: PointScene,
  cta: CtaScene,
};

const renderScene = (scene: Scene) => {
  const Component = SCENES[scene.type] as React.FC<Scene>;
  return <Component {...scene} />;
};

export const ShortsVideo: React.FC<ShortsProps> = ({ scenes }) => (
  <AbsoluteFill>
    <Series>
      {scenes.map((scene, i) => (
        <Series.Sequence key={i} durationInFrames={scene.durationInFrames}>
          {renderScene(scene)}
          {scene.audio ? <Audio src={staticFile(scene.audio)} /> : null}
        </Series.Sequence>
      ))}
    </Series>
    <ProgressBar />
  </AbsoluteFill>
);
