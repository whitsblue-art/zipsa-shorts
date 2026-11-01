import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { ProductImage } from "../components/ProductImage";
import { Stage } from "../components/Stage";
import { Subtitle } from "../components/Subtitle";
import { theme } from "../theme";
import type { CoverScene as Props } from "../types";

/** 첫 씬 = 쇼츠 커버. 0프레임부터 문구가 다 보여야 썸네일로 쓸 수 있다. */
export const CoverScene: React.FC<Props> = ({ headline, subline, highlight, image, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  // 0프레임에 이미 크게 보이고, 살짝 더 커지며 '쿵' 하는 느낌만 준다.
  const punch = spring({ frame, fps, config: { damping: 9, stiffness: 220 } });
  const scale = interpolate(punch, [0, 1], [0.94, 1]);
  const shake = frame < 18 ? Math.sin(frame * 1.6) * (18 - frame) * 0.5 : 0;

  const parts = highlight && headline.includes(highlight) ? headline.split(highlight) : [headline];

  return (
    <Stage>
      <div
        style={{
          marginTop: 40,
          fontSize: 132,
          fontWeight: 900,
          lineHeight: 1.1,
          textAlign: "center",
          wordBreak: "keep-all",
          transform: `scale(${scale}) translateX(${shake}px)`,
          textShadow: "0 8px 0 rgba(0,0,0,0.45)",
        }}
      >
        {parts.length === 2 ? (
          <>
            {parts[0]}
            <span style={{ color: theme.gold }}>{highlight}</span>
            {parts[1]}
          </>
        ) : (
          headline
        )}
      </div>
      <div style={{ marginTop: 24, fontSize: 56, fontWeight: 500, color: theme.muted }}>{subline}</div>
      <div style={{ marginTop: 60 }}>
        <ProductImage src={image} size={640} label="오늘의 집사템" />
      </div>
      <Subtitle text={subtitle} />
    </Stage>
  );
};
