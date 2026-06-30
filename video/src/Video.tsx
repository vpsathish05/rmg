import { Sequence } from "remotion";
import { TitleScene } from "./scenes/TitleScene";
import { InputScene } from "./scenes/InputScene";
import { CoeDetection } from "./scenes/CoeDetection";
import { SemanticMatch } from "./scenes/SemanticMatch";
import { FormulaScore } from "./scenes/FormulaScore";
import { AiEnrichment } from "./scenes/AiEnrichment";
import { OutputScene } from "./scenes/OutputScene";
import { SCENES } from "./styles/brand";

export const AiEngineVideo: React.FC = () => {
  return (
    <>
      <Sequence from={SCENES.title.start} durationInFrames={SCENES.title.duration}>
        <TitleScene />
      </Sequence>

      <Sequence from={SCENES.input.start} durationInFrames={SCENES.input.duration}>
        <InputScene />
      </Sequence>

      <Sequence from={SCENES.coe.start} durationInFrames={SCENES.coe.duration}>
        <CoeDetection />
      </Sequence>

      <Sequence from={SCENES.semantic.start} durationInFrames={SCENES.semantic.duration}>
        <SemanticMatch />
      </Sequence>

      <Sequence from={SCENES.formula.start} durationInFrames={SCENES.formula.duration}>
        <FormulaScore />
      </Sequence>

      <Sequence from={SCENES.enrichment.start} durationInFrames={SCENES.enrichment.duration}>
        <AiEnrichment />
      </Sequence>

      <Sequence from={SCENES.output.start} durationInFrames={SCENES.output.duration}>
        <OutputScene />
      </Sequence>
    </>
  );
};
