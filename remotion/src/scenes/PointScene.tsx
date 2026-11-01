import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { ProductImage } from "../components/ProductImage";
import { Stage } from "../components/Stage";
import { Subtitle } from "../components/Subtitle";
import { theme } from "../theme";
import type { PointScene as Props } from "../types";

/** 이점 하나: 번호 배지 + 큰 제목 + 체크. 이미지가 있으면 위에 작게. */
export const PointScene: React.FC<Props> = ({ index, title, detail, image, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const badge = spring({ frame, fps, config: { damping: 9, stiffness: 180 } });
  const titleIn = spring({ frame: frame - 6, fps, config: { damping: 200 } });
  const check = spring({ frame: frame - 18, fps, config: { damping: 8 } });

  return (
    <Stage>
      {image ? (
        <div style={{ marginTop: 20, opacity: titleIn }}>
          <ProductImage src={image} size={560} />
        </div>
      ) : (
        <div style={{ height: 240 }} />
      )}
      <div
        style={{
          marginTop: 50,
          width: 150,
          height: 150,
          borderRadius: 75,
          background: theme.gold,
          color: theme.bg,
          fontSize: 92,
          fontWeight: 900,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          transform: `scale(${badge})`,
        }}
      >
        {index}
      </div>
      <div
        style={{
          marginTop: 36,
          fontSize: 96,
          fontWeight: 900,
          textAlign: "center",
          wordBreak: "keep-all",
          lineHeight: 1.15,
          opacity: titleIn,
          transform: `translateX(${interpolate(titleIn, [0, 1], [-120, 0])}px)`,
        }}
      >
        {title} <span style={{ color: theme.gold, display: "inline-block", transform: `scale(${check})` }}>✓</span>
      </div>
      {detail ? (
        <div style={{ marginTop: 24, fontSize: 50, color: theme.muted, textAlign: "center", opacity: titleIn }}>
          {detail}
        </div>
      ) : null}
      <Subtitle text={subtitle} />
    </Stage>
  );
};
