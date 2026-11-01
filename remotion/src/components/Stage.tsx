import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";
import { fontFamily, theme } from "../theme";

/** 모든 씬의 바탕: 배경 그라디언트, 안전 영역 패딩, 상단 채널 배지. */
export const Stage: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const glow = interpolate(frame, [0, durationInFrames], [0, 40]);

  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle at 50% ${30 + glow / 4}%, #262A3A 0%, ${theme.bg} 60%)`,
        fontFamily,
        color: theme.white,
      }}
    >
      <AbsoluteFill
        style={{
          paddingTop: theme.safeTop,
          paddingBottom: theme.safeBottom,
          paddingLeft: 70,
          paddingRight: 70,
          alignItems: "center",
        }}
      >
        {children}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

/** 영상 전체 진행 바 (최상단 레이어에 한 번만 그린다). */
export const ProgressBar: React.FC = () => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return (
    <div
      style={{
        position: "absolute",
        top: theme.safeTop - 40,
        left: 70,
        right: 70,
        height: 8,
        borderRadius: 4,
        background: "rgba(255,255,255,0.15)",
      }}
    >
      <div
        style={{
          width: `${(frame / durationInFrames) * 100}%`,
          height: "100%",
          borderRadius: 4,
          background: theme.gold,
        }}
      />
    </div>
  );
};
