import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";

const FIELDS = [
  { label: "Client", value: "Sigma Healthcare" },
  { label: "Role", value: "Senior Data Engineer" },
  { label: "COE", value: "Data Engineering" },
  { label: "Skills Required", value: "Python, Spark, Azure, SQL" },
  { label: "Allocation", value: "100%" },
  { label: "Duration", value: "12 weeks" },
  { label: "Status", value: "Not Resourced" },
];

export const InputScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Section title
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Card entrance
  const cardScale = spring({
    frame: frame - 15,
    fps,
    config: { damping: 14, stiffness: 100 },
  });
  const cardOpacity = interpolate(frame, [15, 30], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // "This triggers the AI pipeline" label
  const triggerOpacity = interpolate(frame, [140, 160], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const triggerY = interpolate(frame, [140, 160], [20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Pulsing glow on status
  const pulseOpacity = 0.3 + 0.3 * Math.sin(frame * 0.1);

  return (
    <AbsoluteFill
      style={{
        background: COLORS.white,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 80,
      }}
    >
      {/* Section title */}
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 80,
          opacity: titleOpacity,
        }}
      >
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
          STEP 1
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
          Pipeline Role Request
        </h2>
      </div>

      {/* Role Card */}
      <div
        style={{
          transform: `scale(${cardScale})`,
          opacity: cardOpacity,
          width: 700,
          border: `2px solid ${COLORS.midnightBlue}`,
          background: COLORS.white,
          overflow: "hidden",
        }}
      >
        {/* Card header */}
        <div
          style={{
            background: COLORS.midnightBlue,
            padding: "20px 32px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <span
            style={{
              fontFamily: FONT.family,
              fontSize: FONT.body.size,
              fontWeight: "bold",
              color: COLORS.white,
            }}
          >
            Pipeline Request #47
          </span>
          <span
            style={{
              fontFamily: FONT.family,
              fontSize: FONT.small.size,
              fontWeight: "bold",
              color: COLORS.rose,
              background: "rgba(255,97,150,0.15)",
              padding: "4px 12px",
              border: `1px solid ${COLORS.rose}`,
            }}
          >
            NOT RESOURCED
          </span>
        </div>

        {/* Card body */}
        <div style={{ padding: "24px 32px" }}>
          {FIELDS.map((field, i) => {
            const fieldDelay = 30 + i * 12;
            const fieldOpacity = interpolate(frame, [fieldDelay, fieldDelay + 12], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });
            const fieldX = interpolate(frame, [fieldDelay, fieldDelay + 12], [-20, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            });

            return (
              <div
                key={field.label}
                style={{
                  display: "flex",
                  alignItems: "center",
                  padding: "10px 0",
                  borderBottom: i < FIELDS.length - 1 ? `1px solid ${COLORS.greyLight}` : "none",
                  opacity: fieldOpacity,
                  transform: `translateX(${fieldX}px)`,
                }}
              >
                <span
                  style={{
                    fontFamily: FONT.family,
                    fontSize: FONT.body.size,
                    color: COLORS.midnightBlue,
                    fontWeight: "bold",
                    width: 200,
                  }}
                >
                  {field.label}
                </span>
                <span
                  style={{
                    fontFamily: FONT.family,
                    fontSize: FONT.body.size,
                    color: field.label === "Status" ? COLORS.rose : COLORS.trypanBlue,
                    fontWeight: field.label === "Status" ? "bold" : "normal",
                  }}
                >
                  {field.value}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Trigger label */}
      <div
        style={{
          marginTop: 40,
          opacity: triggerOpacity,
          transform: `translateY(${triggerY}px)`,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            width: 12,
            height: 12,
            background: COLORS.rose,
            opacity: pulseOpacity + 0.5,
            boxShadow: `0 0 12px ${COLORS.rose}`,
          }}
        />
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.body.size,
            color: COLORS.midnightBlue,
            margin: 0,
          }}
        >
          This triggers the <strong>8-step AI pipeline</strong>
        </p>
      </div>
    </AbsoluteFill>
  );
};
