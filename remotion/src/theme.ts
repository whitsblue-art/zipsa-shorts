import { loadFont } from "@remotion/google-fonts/NotoSansKR";

export const { fontFamily } = loadFont("normal", {
  weights: ["500", "900"],
  ignoreTooManyRequestsWarning: true,
});

export const theme = {
  bg: "#12141C",
  panel: "#0A0C12",
  gold: "#D4AF37",
  white: "#FFFFFF",
  muted: "#9AA0B4",
  red: "#E5484D",
  width: 1080,
  height: 1920,
  /** 유튜브 쇼츠 UI가 가리는 위·아래 영역 */
  safeTop: 250,
  safeBottom: 330,
};
