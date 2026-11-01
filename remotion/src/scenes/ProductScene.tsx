import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { ProductImage } from "../components/ProductImage";
import { Stage } from "../components/Stage";
import { Subtitle } from "../components/Subtitle";
import { theme } from "../theme";
import type { ProductScene as Props } from "../types";

/** 해결책 등장: 상품이 아래에서 튀어오르고 빛 번짐 + 라벨. */
export const ProductScene: React.FC<Props> = ({ image, label, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame, fps, config: { damping: 10, stiffness: 120 } });
  const zoom = interpolate(frame, [0, 150], [1, 1.06], { extrapolateRight: "clamp" });
  const labelIn = spring({ frame: frame - 12, fps, config: { damping: 200 } });

  return (
    <Stage>
      <div
        style={{
          marginTop: 60,
          transform: `translateY(${interpolate(pop, [0, 1], [500, 0])}px) scale(${zoom})`,
          filter: `drop-shadow(0 0 ${interpolate(pop, [0, 1], [0, 60])}px ${theme.gold}55)`,
        }}
      >
        <ProductImage src={image} size={860} label={label} />
      </div>
      <div
        style={{
          marginTop: 50,
          padding: "16px 40px",
          borderRadius: 999,
          background: theme.gold,
          color: theme.bg,
          fontSize: 54,
          fontWeight: 900,
          opacity: labelIn,
          transform: `scale(${interpolate(labelIn, [0, 1], [0.6, 1])})`,
        }}
      >
        {label}
      </div>
      <Subtitle text={subtitle} />
    </Stage>
  );
};
