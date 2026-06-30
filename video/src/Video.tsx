import React from "react";
import { Sequence, useCurrentFrame, interpolate, AbsoluteFill } from "remotion";
import { TitleScene } from "./scenes/TitleScene";
import { InputScene } from "./scenes/InputScene";
import { CoeDetection } from "./scenes/CoeDetection";
import { SemanticMatch } from "./scenes/SemanticMatch";
import { FormulaScore } from "./scenes/FormulaScore";
import { AiEnrichment } from "./scenes/AiEnrichment";
import { OutputScene } from "./scenes/OutputScene";
import { SCENES } from "./styles/brand";

// Fade wrapper — fades in at start and out at end of each scene
const FadeScene: React.FC<{
  children: React.ReactNode;
  duration: number;
  fadeIn?: number;
  fadeOut?: number;
}> = ({ children, duration, fadeIn = 15, fadeOut = 10 }) => {
  const frame = useCurrentFrame();

  const opacity = interpolate(
    frame,
    [0, fadeIn, duration - fadeOut, duration],
    [0, 1, 1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  return (
    <AbsoluteFill style={{ opacity }}>
      {children}
    </AbsoluteFill>
  );
};

export const AiEngineVideo: React.FC = () => {
  return (
    <>
      <Sequence from={SCENES.title.start} durationInFrames={SCENES.title.duration}>
        <FadeScene duration={SCENES.title.duration} fadeIn={0} fadeOut={12}>
          <TitleScene />
        </FadeScene>
      </Sequence>

      <Sequence from={SCENES.input.start} durationInFrames={SCENES.input.duration}>
        <FadeScene duration={SCENES.input.duration}>
          <InputScene />
        </FadeScene>
      </Sequence>

      <Sequence from={SCENES.coe.start} durationInFrames={SCENES.coe.duration}>
        <FadeScene duration={SCENES.coe.duration}>
          <CoeDetection />
        </FadeScene>
      </Sequence>

      <Sequence from={SCENES.semantic.start} durationInFrames={SCENES.semantic.duration}>
        <FadeScene duration={SCENES.semantic.duration}>
          <SemanticMatch />
        </FadeScene>
      </Sequence>

      <Sequence from={SCENES.formula.start} durationInFrames={SCENES.formula.duration}>
        <FadeScene duration={SCENES.formula.duration}>
          <FormulaScore />
        </FadeScene>
      </Sequence>

      <Sequence from={SCENES.enrichment.start} durationInFrames={SCENES.enrichment.duration}>
        <FadeScene duration={SCENES.enrichment.duration}>
          <AiEnrichment />
        </FadeScene>
      </Sequence>

      <Sequence from={SCENES.output.start} durationInFrames={SCENES.output.duration}>
        <FadeScene duration={SCENES.output.duration} fadeOut={20}>
          <OutputScene />
        </FadeScene>
      </Sequence>
    </>
  );
};
