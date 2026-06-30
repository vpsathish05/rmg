import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";
import { FlowNode } from "../components/FlowNode";
import { Arrow } from "../components/Arrow";

export const CoeDetection: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Section title
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Decision flow: 3 nodes light up sequentially
  // Node 1: SQL Role-Based (frame 30)
  // Node 2: SQL Global Fallback (frame 90)
  // Node 3: GPT-4o Inference (frame 150)

  // "X" marks for failed attempts
  const x1Opacity = interpolate(frame, [70, 80], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const x2Opacity = interpolate(frame, [130, 140], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Checkmark for success
  const checkOpacity = interpolate(frame, [190, 200], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Result bubble
  const resultOpacity = interpolate(frame, [200, 220], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const resultScale = spring({
    frame: frame - 200,
    fps,
    config: { damping: 12, stiffness: 100 },
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
          STEP 2
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
          COE Detection
        </h2>
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.body.size,
            color: COLORS.trypanBlue,
            margin: "8px 0 0",
          }}
        >
          Which Centre of Excellence does this role belong to?
        </p>
      </div>

      {/* Flow: 3 nodes horizontally with arrows */}
      {/* Node 1: SQL Role-Based */}
      <FlowNode
        label="SQL Role-Based"
        subtitle="Match canonical_role → employee_skills"
        variant="primary"
        delay={30}
        x={150}
        y={300}
        width={340}
        height={90}
      />

      {/* Arrow 1→2 */}
      <Arrow x1={490} y1={345} x2={610} y2={345} delay={55} />

      {/* X mark on node 1 */}
      <div
        style={{
          position: "absolute",
          left: 260,
          top: 400,
          opacity: x1Opacity,
          fontFamily: FONT.family,
          fontSize: 20,
          fontWeight: "bold",
          color: COLORS.red,
          background: "rgba(255,0,0,0.08)",
          padding: "4px 12px",
          border: `1px solid ${COLORS.red}`,
        }}
      >
        &#10007; No match found
      </div>

      {/* Node 2: SQL Global Fallback */}
      <FlowNode
        label="SQL Global Fallback"
        subtitle="Most common COE across all employees"
        variant="secondary"
        delay={90}
        x={620}
        y={300}
        width={320}
        height={90}
      />

      {/* Arrow 2→3 */}
      <Arrow x1={940} y1={345} x2={1060} y2={345} delay={115} />

      {/* X mark on node 2 */}
      <div
        style={{
          position: "absolute",
          left: 700,
          top: 400,
          opacity: x2Opacity,
          fontFamily: FONT.family,
          fontSize: 20,
          fontWeight: "bold",
          color: COLORS.red,
          background: "rgba(255,0,0,0.08)",
          padding: "4px 12px",
          border: `1px solid ${COLORS.red}`,
        }}
      >
        &#10007; No match found
      </div>

      {/* Node 3: GPT-4o */}
      <FlowNode
        label="GPT-4o Inference"
        subtitle="LLM infers COE from role name + skills"
        variant="highlight"
        delay={150}
        x={1060}
        y={300}
        width={320}
        height={90}
      />

      {/* Checkmark on node 3 */}
      <div
        style={{
          position: "absolute",
          left: 1140,
          top: 400,
          opacity: checkOpacity,
          fontFamily: FONT.family,
          fontSize: 20,
          fontWeight: "bold",
          color: COLORS.green,
          background: "rgba(0,176,80,0.08)",
          padding: "4px 12px",
          border: `1px solid ${COLORS.green}`,
        }}
      >
        &#10003; Match: Data Engineering
      </div>

      {/* Description under the flow */}
      <div
        style={{
          position: "absolute",
          left: 150,
          top: 450,
          width: 1300,
          display: "flex",
          justifyContent: "space-between",
          opacity: interpolate(frame, [60, 80], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          }),
        }}
      >
        {["Try 1: Fast SQL lookup", "Try 2: Broader SQL scan", "Try 3: AI fallback"].map((text, i) => (
          <p
            key={i}
            style={{
              fontFamily: FONT.family,
              fontSize: FONT.small.size,
              color: COLORS.midnightBlue,
              opacity: 0.6,
              margin: 0,
              width: 340,
              textAlign: "center",
            }}
          >
            {text}
          </p>
        ))}
      </div>

      {/* Result bubble */}
      <div
        style={{
          position: "absolute",
          left: 660,
          top: 560,
          transform: `scale(${resultScale})`,
          opacity: resultOpacity,
          display: "flex",
          alignItems: "center",
          gap: 16,
          background: COLORS.greyLight,
          border: `2px solid ${COLORS.midnightBlue}`,
          padding: "20px 40px",
        }}
      >
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.body.size,
            color: COLORS.midnightBlue,
          }}
        >
          Detected COE:
        </span>
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.subheading.size,
            fontWeight: "bold",
            color: COLORS.trypanBlue,
          }}
        >
          Data Engineering
        </span>
      </div>

      {/* Bottom note */}
      <div
        style={{
          position: "absolute",
          bottom: 80,
          left: 150,
          opacity: resultOpacity,
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            color: COLORS.midnightBlue,
            opacity: 0.5,
            margin: 0,
          }}
        >
          Cascading fallback ensures a COE is always identified — SQL is fast, GPT-4o is the safety net
        </p>
      </div>
    </AbsoluteFill>
  );
};
