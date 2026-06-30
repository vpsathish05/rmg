import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";
import { FlowNode } from "../components/FlowNode";
import { Arrow } from "../components/Arrow";

export const AiEnrichment: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // GPT-4o central icon pulse
  const gptPulse = 0.9 + 0.1 * Math.sin(frame * 0.12);

  // Three parallel tracks reveal
  const track1Opacity = interpolate(frame, [40, 60], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const track2Opacity = interpolate(frame, [80, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const track3Opacity = interpolate(frame, [120, 140], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Output cards
  const out1Opacity = interpolate(frame, [150, 170], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const out2Opacity = interpolate(frame, [180, 200], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const out3Opacity = interpolate(frame, [210, 230], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "Parallel" badge
  const parallelOpacity = interpolate(frame, [250, 270], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill
      style={{
        background: COLORS.white,
        padding: 80,
      }}
    >
      {/* Section header */}
      <div style={{ opacity: titleOpacity }}>
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            fontWeight: "bold",
            color: COLORS.rose,
            textTransform: "uppercase",
            letterSpacing: 3,
            margin: 0,
          }}
        >
          STEPS 5-7
        </p>
        <h2
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.heading.size,
            fontWeight: "bold",
            color: COLORS.midnightBlue,
            margin: "8px 0 0",
          }}
        >
          AI Enrichment
        </h2>
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.body.size,
            color: COLORS.trypanBlue,
            margin: "8px 0 0",
          }}
        >
          Three parallel GPT-4o tasks enrich the top 10 candidates
        </p>
      </div>

      {/* Central GPT-4o node */}
      <div
        style={{
          position: "absolute",
          left: 160,
          top: 350,
          transform: `scale(${gptPulse})`,
          background: COLORS.midnightBlue,
          padding: "20px 30px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 4,
          boxShadow: `0 0 30px rgba(25,16,91,0.3)`,
        }}
      >
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.subheading.size,
            fontWeight: "bold",
            color: COLORS.white,
          }}
        >
          GPT-4o
        </span>
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.turquoise,
          }}
        >
          Top 10 candidates
        </span>
      </div>

      {/* Arrows from GPT to tracks */}
      <Arrow x1={330} y1={350} x2={480} y2={280} delay={35} color={COLORS.trypanBlue} />
      <Arrow x1={330} y1={380} x2={480} y2={420} delay={75} color={COLORS.rose} />
      <Arrow x1={330} y1={410} x2={480} y2={560} delay={115} color={COLORS.emerald} />

      {/* Track 1: Rationale */}
      <div style={{ position: "absolute", left: 480, top: 240, opacity: track1Opacity }}>
        <FlowNode
          label="Rationale Generation"
          subtitle="2-3 sentence explanation per candidate"
          variant="primary"
          delay={0}
          x={0}
          y={0}
          width={380}
          height={80}
        />
      </div>

      {/* Track 1 Output */}
      <div
        style={{
          position: "absolute",
          left: 900,
          top: 245,
          opacity: out1Opacity,
          background: COLORS.greyLight,
          border: `1px solid ${COLORS.trypanBlue}`,
          padding: "12px 20px",
          width: 450,
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.midnightBlue,
            margin: 0,
            fontStyle: "italic",
            lineHeight: 1.5,
          }}
        >
          "EMP_042 has strong Spark and Python skills (87% match), is currently 100% available, and has delivered
          similar Data Engineering projects for healthcare clients."
        </p>
      </div>

      {/* Track 2: Re-Ranking */}
      <div style={{ position: "absolute", left: 480, top: 380, opacity: track2Opacity }}>
        <FlowNode
          label="LLM Re-Ranking"
          subtitle="Holistic reorder based on overall fit"
          variant="highlight"
          delay={0}
          x={0}
          y={0}
          width={380}
          height={80}
        />
      </div>

      {/* Track 2 Output */}
      <div
        style={{
          position: "absolute",
          left: 900,
          top: 385,
          opacity: out2Opacity,
          background: COLORS.greyLight,
          border: `1px solid ${COLORS.rose}`,
          padding: "12px 20px",
          width: 450,
        }}
      >
        <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
          {["EMP_042", "EMP_015", "EMP_088"].map((id, i) => (
            <div
              key={id}
              style={{
                background: i === 0 ? COLORS.rose : COLORS.greyLight,
                border: `1px solid ${COLORS.rose}`,
                padding: "6px 12px",
                fontFamily: FONT.family,
                fontSize: FONT.small.size,
                fontWeight: "bold",
                color: i === 0 ? COLORS.white : COLORS.midnightBlue,
              }}
            >
              #{i + 1} {id}
            </div>
          ))}
        </div>
      </div>

      {/* Track 3: KB Proof */}
      <div style={{ position: "absolute", left: 480, top: 520, opacity: track3Opacity }}>
        <FlowNode
          label="KB Proof Search"
          subtitle="pgvector: past project evidence per candidate"
          variant="accent"
          delay={0}
          x={0}
          y={0}
          width={380}
          height={80}
        />
      </div>

      {/* Track 3 Output */}
      <div
        style={{
          position: "absolute",
          left: 900,
          top: 525,
          opacity: out3Opacity,
          background: COLORS.greyLight,
          border: `1px solid ${COLORS.emerald}`,
          padding: "12px 20px",
          width: 450,
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.midnightBlue,
            margin: 0,
            lineHeight: 1.4,
          }}
        >
          Proof: EMP_042 worked on PROJECT_089 (Data Eng, Sigma) — 92% similarity
        </p>
      </div>

      {/* Parallel execution badge */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 480,
          opacity: parallelOpacity,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            background: COLORS.midnightBlue,
            padding: "10px 20px",
          }}
        >
          <span
            style={{
              fontFamily: FONT.family,
              fontSize: FONT.caption.size,
              fontWeight: "bold",
              color: COLORS.turquoise,
            }}
          >
            asyncio.gather()
          </span>
        </div>
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            color: COLORS.midnightBlue,
            opacity: 0.6,
          }}
        >
          All three run in parallel for speed
        </span>
      </div>
    </AbsoluteFill>
  );
};
