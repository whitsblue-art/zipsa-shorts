// content/<slug>/scenes.json 형식. /yt-editor가 이 타입에 맞춰 씬 데이터를 쓴다.

type Base = {
  /** TTS로 읽을 문장. scripts/tts.py가 음성을 만든다. */
  narration: string;
  /** 하단 자막. **굵게** 표시한 부분은 골드로 강조된다. */
  subtitle: string;
  /** remotion/public 기준 mp3 경로. tts.py가 채운다. */
  audio?: string;
  /** 씬 길이(프레임). tts.py가 음성 길이에 맞춰 채운다. */
  durationInFrames: number;
};

export type CoverScene = Base & {
  type: "cover";
  headline: string;
  subline: string;
  /** headline 안에서 골드로 칠할 단어 */
  highlight?: string;
  image?: string;
};

export type ProblemScene = Base & {
  type: "problem";
  /** 큰 글자로 보여줄 이모지나 짧은 단어 */
  icon: string;
  caption: string;
};

export type ProductScene = Base & {
  type: "product";
  /** remotion/public 기준 상품 이미지 경로. 비우면 자리표시 카드 */
  image?: string;
  label: string;
};

export type PointScene = Base & {
  type: "point";
  /** 1, 2, 3 ... 이점 번호 */
  index: number;
  title: string;
  detail?: string;
  image?: string;
};

export type CtaScene = Base & {
  type: "cta";
  productNumber: string;
  channelName: string;
};

export type Scene = CoverScene | ProblemScene | ProductScene | PointScene | CtaScene;

export type ShortsProps = {
  slug: string;
  fps: number;
  voice?: string;
  rate?: string;
  scenes: Scene[];
};
