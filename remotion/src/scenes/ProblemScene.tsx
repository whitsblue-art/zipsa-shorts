import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { Stage } from "../components/Stage";
import { Subtitle } from "../components/Subtitle";
import { theme } from "../theme";
import type { ProblemScene as Props } from "../types";

/** 문제 상황: 큰 아이콘이 흔들리다가 빨간 X가 찍힌다. */
export const ProblemScene: React.FC<Props> = ({ icon, caption, subtitle }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const wobble = Math.sin(frame / 3) * 6;
  const enter = spring({ frame, fps, config: { damping: 12 } });
  const xMark = spring({ frame: frame - 20, fps, config: { damping: 8, stiffness: 200 } });

  return (
    <Stage>
      <div
        style={{
          marginTop: 120,
          position: "relative",
          width: 620,
          height: 620,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
        }}
      >
        <div
          style={{
            fontSize: 380,
            transform: `scale(${enter}) rotate(${wobble}deg)`,
          }}
        >
          {icon}
        </div>
        <div
          style={{
            position: "absolute",
            fontSize: 560,
            fontWeight: 900,
            color: theme.red,
            opacity: interpolate(xMark, [0, 1], [0, 0.9]),
            transform: `scale(${interpolate(xMark, [0, 1], [2, 1])})`,
          }}
        >
          ✕
        </div>
      </div>
      <div
        style={{
          marginTop: 40,
          fontSize: 68,
          fontWeight: 900,
          textAlign: "center",
          wordBreak: "keep-all",
          opacity: enter,
        }}
      >
        {caption}
      </div>
      <Subtitle text={subtitle} />
    </Stage>
  );
};
