import React from "react";
import { Img, staticFile } from "remotion";
import { theme } from "../theme";

/** 상품 이미지. 경로가 없으면 자리표시 카드를 그린다 (쿠팡 이미지 받기 전 미리보기용). */
export const ProductImage: React.FC<{ src?: string; size: number; label?: string }> = ({
  src,
  size,
  label,
}) => {
  const frameStyle: React.CSSProperties = {
    width: size,
    height: size,
    borderRadius: 32,
    border: `5px solid ${theme.gold}`,
    boxShadow: "0 30px 80px rgba(0,0,0,0.55)",
    overflow: "hidden",
    background: "#1E2130",
  };
  if (src) {
    return <Img src={staticFile(src)} style={{ ...frameStyle, objectFit: "cover" }} />;
  }
  return (
    <div
      style={{
        ...frameStyle,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 20,
        color: theme.muted,
        fontSize: 44,
        fontWeight: 500,
      }}
    >
      <div style={{ fontSize: size * 0.3 }}>📦</div>
      {label ?? "상품 이미지"}
    </div>
  );
};
