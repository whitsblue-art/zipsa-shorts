import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { theme } from "../theme";

/** "**강조**" 부분을 골드로 칠한다. */
export const RichText: React.FC<{ text: string; highlightColor?: string }> = ({
  text,
  highlightColor = theme.gold,
}) => (
  <>
    {text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
      part.startsWith("**") && part.endsWith("**") ? (
        <span key={i} style={{ color: highlightColor }}>
          {part.slice(2, -2)}
        </span>
      ) : (
        <React.Fragment key={i}>{part}</React.Fragment>
      ),
    )}
  </>
);

/** 하단 자막 박스. 씬 시작 시 아래에서 튀어오른다. */
export const Subtitle: React.FC<{ text: string }> = ({ text }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame, fps, config: { damping: 14, stiffness: 160 } });

  return (
    <div
      style={{
        position: "absolute",
        bottom: theme.safeBottom,
        left: 60,
        right: 60,
        padding: "34px 40px",
        background: theme.panel,
        borderTop: `6px solid ${theme.gold}`,
        borderRadius: 18,
        fontSize: 58,
        fontWeight: 900,
        lineHeight: 1.3,
        textAlign: "center",
        wordBreak: "keep-all",
        opacity: interpolate(enter, [0, 1], [0, 1]),
        transform: `translateY(${interpolate(enter, [0, 1], [80, 0])}px)`,
      }}
    >
      <RichText text={text} />
    </div>
  );
};
