import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";
import { AnimatedBar } from "../components/AnimatedBar";

export const FormulaScore: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Formula text reveal
  const formulaOpacity = interpolate(frame, [30, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Blend explanation
  const blendOpacity = interpolate(frame, [200, 220], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Total score result
  const totalOpacity = interpolate(frame, [270, 290], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const totalScale = spring({
    frame: frame - 270,
    fps,
    config: { damping: 12, stiffness: 100 },
  });

  // Availability note
  const availNoteOpacity = interpolate(frame, [160, 180], [0, 1], {
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
          STEP 4
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
          Formula Scoring
        </h2>
      </div>

      {/* Formula */}
      <div
        style={{
          position: "absolute",
          top: 180,
          left: 200,
          opacity: formulaOpacity,
          background: COLORS.greyLight,
          border: `2px solid ${COLORS.midnightBlue}`,
          padding: "16px 32px",
        }}
      >
        <span
          style={{
            fontFamily: "monospace",
            fontSize: 22,
            color: COLORS.midnightBlue,
            fontWeight: "bold",
          }}
        >
          total = skill
          <span style={{ color: COLORS.trypanBlue }}> x0.40 </span>
          + competency
          <span style={{ color: COLORS.rose }}> x0.25 </span>
          + availability
          <span style={{ color: COLORS.turquoise }}> x0.25 </span>
          + productivity
          <span style={{ color: COLORS.amethyst }}> x0.10</span>
        </span>
      </div>

      {/* Animated score bars */}
      <AnimatedBar
        label="Skill"
        value={0.82}
        weight="0.40"
        color={COLORS.trypanBlue}
        delay={70}
        y={310}
        barWidth={550}
      />
      <AnimatedBar
        label="Competency"
        value={0.68}
        weight="0.25"
        color={COLORS.rose}
        delay={100}
        y={380}
        barWidth={550}
      />
      <AnimatedBar
        label="Availability"
        value={1.0}
        weight="0.25"
        color={COLORS.turquoise}
        delay={130}
        y={450}
        barWidth={550}
      />
      <AnimatedBar
        label="Productivity"
        value={0.91}
        weight="0.10"
        color={COLORS.amethyst}
        delay={160}
        y={520}
        barWidth={550}
      />

      {/* Availability note */}
      <div
        style={{
          position: "absolute",
          left: 870,
          top: 450,
          opacity: availNoteOpacity,
          background: COLORS.turquoise,
          padding: "8px 16px",
          maxWidth: 380,
        }}
      >
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.midnightBlue,
            fontWeight: "bold",
          }}
        >
          Relative scoring: 1.0 if capacity meets requested allocation
        </span>
      </div>

      {/* Skill blend explanation */}
      <div
        style={{
          position: "absolute",
          left: 870,
          top: 310,
          opacity: blendOpacity,
          background: COLORS.greyLight,
          border: `1px solid ${COLORS.grey}`,
          padding: "12px 20px",
          maxWidth: 400,
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            fontWeight: "bold",
            color: COLORS.midnightBlue,
            margin: "0 0 4px",
          }}
        >
          Skill Score Blend:
        </p>
        <p
          style={{
            fontFamily: "monospace",
            fontSize: 14,
            color: COLORS.trypanBlue,
            margin: 0,
          }}
        >
          50% COE assessment + 50% semantic similarity
        </p>
      </div>

      {/* Total Score Result */}
      <div
        style={{
          position: "absolute",
          left: 350,
          top: 620,
          opacity: totalOpacity,
          transform: `scale(${totalScale})`,
          display: "flex",
          alignItems: "center",
          gap: 24,
        }}
      >
        {/* Calculation */}
        <div
          style={{
            fontFamily: "monospace",
            fontSize: 18,
            color: COLORS.midnightBlue,
            opacity: 0.7,
          }}
        >
          (0.82 x 0.40) + (0.68 x 0.25) + (1.00 x 0.25) + (0.91 x 0.10) =
        </div>

        {/* Score badge */}
        <div
          style={{
            background: COLORS.midnightBlue,
            padding: "16px 32px",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
          }}
        >
          <span
            style={{
              fontFamily: FONT.family,
              fontSize: 14,
              color: COLORS.turquoise,
              fontWeight: "bold",
              textTransform: "uppercase",
              letterSpacing: 2,
            }}
          >
            TOTAL SCORE
          </span>
          <span
            style={{
              fontFamily: FONT.family,
              fontSize: 48,
              fontWeight: "bold",
              color: COLORS.white,
            }}
          >
            0.839
          </span>
        </div>
      </div>

      {/* Category logic */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 200,
          opacity: totalOpacity,
          display: "flex",
          gap: 32,
        }}
      >
        {[
          { label: "Available", desc: "Has capacity for role", color: COLORS.green },
          { label: "BestMatch", desc: "Score >= 0.40, allocated", color: COLORS.trypanBlue },
          { label: "Stretch", desc: "Low fit & allocated", color: COLORS.grey },
        ].map((cat) => (
          <div key={cat.label} style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <div style={{ width: 14, height: 14, background: cat.color }} />
            <div>
              <span
                style={{
                  fontFamily: FONT.family,
                  fontSize: FONT.small.size,
                  fontWeight: "bold",
                  color: COLORS.midnightBlue,
                }}
              >
                {cat.label}
              </span>
              <span
                style={{
                  fontFamily: FONT.family,
                  fontSize: 12,
                  color: COLORS.midnightBlue,
                  opacity: 0.6,
                  marginLeft: 6,
                }}
              >
                {cat.desc}
              </span>
            </div>
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
