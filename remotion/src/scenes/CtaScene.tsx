import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage } from "../components/Stage";
import { Subtitle } from "../components/Subtitle";
import { theme } from "../theme";
import type { CtaScene as Props } from "../types";

/** 행동 유도: 상품 번호 배지가 맥박처럼 뛰고, 프로필 링크 안내. */
export const CtaScene: React.FC<Props> = ({ productNumber, channelName, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 10, stiffness: 140 } });
  const pulse = 1 + Math.sin(frame / 5) * 0.03;
  const arrow = interpolate(frame % 30, [0, 15, 30], [0, -24, 0]);

  return (
    <Stage>
      <div style={{ marginTop: 140, fontSize: 64, fontWeight: 500, color: theme.muted }}>프로필 링크</div>
      <div style={{ marginTop: 10, fontSize: 96, fontWeight: 900 }}>[{channelName}]</div>
      <div
        style={{
          marginTop: 70,
          width: 560,
          height: 560,
          borderRadius: 280,
          border: `10px solid ${theme.gold}`,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${enter * pulse})`,
          background: "rgba(212,175,55,0.08)",
        }}
      >
        <div style={{ fontSize: 220, fontWeight: 900, color: theme.gold, lineHeight: 1 }}>{productNumber}</div>
        <div style={{ fontSize: 64, fontWeight: 900 }}>번 검색</div>
      </div>
      <div style={{ marginTop: 50, fontSize: 110, transform: `translateY(${arrow}px)` }}>☝️</div>
      <Subtitle text={subtitle} />
    </Stage>
  );
};
