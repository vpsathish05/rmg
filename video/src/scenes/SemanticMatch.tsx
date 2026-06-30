import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";
import { GlowDot } from "../components/GlowDot";

// Simulated employee dots in vector space
const EMPLOYEES = [
  { id: "EMP_042", x: 720, y: 380, similarity: 0.87, highlight: true },
  { id: "EMP_015", x: 780, y: 420, similarity: 0.82, highlight: true },
  { id: "EMP_088", x: 850, y: 350, similarity: 0.76, highlight: true },
  { id: "EMP_023", x: 600, y: 500, similarity: 0.61, highlight: false },
  { id: "EMP_091", x: 950, y: 480, similarity: 0.55, highlight: false },
  { id: "EMP_017", x: 500, y: 350, similarity: 0.44, highlight: false },
  { id: "EMP_064", x: 1050, y: 550, similarity: 0.38, highlight: false },
  { id: "EMP_033", x: 450, y: 600, similarity: 0.32, highlight: false },
  { id: "EMP_078", x: 1150, y: 400, similarity: 0.28, highlight: false },
  { id: "EMP_055", x: 350, y: 450, similarity: 0.21, highlight: false },
  { id: "EMP_099", x: 1200, y: 600, similarity: 0.15, highlight: false },
  { id: "EMP_012", x: 300, y: 550, similarity: 0.12, highlight: false },
];

export const SemanticMatch: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Role query embedding animation
  const queryOpacity = interpolate(frame, [25, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const queryScale = spring({
    frame: frame - 25,
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  // Vector space dots appear (used for timing reference)
  const _dotsPhase = interpolate(frame, [60, 100], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Search radius expands from query point
  const radiusProgress = interpolate(frame, [110, 160], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const searchRadius = radiusProgress * 250;

  // Highlight top-K
  const highlightOpacity = interpolate(frame, [170, 190], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Result labels
  const resultOpacity = interpolate(frame, [210, 240], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // ANN label
  const annOpacity = interpolate(frame, [250, 270], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Query point position (center of the cluster)
  const queryX = 750;
  const queryY = 400;

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
          STEP 3
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
          Semantic Skill Matching
        </h2>
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.body.size,
            color: COLORS.trypanBlue,
            margin: "8px 0 0",
          }}
        >
          Embed role query → pgvector ANN finds nearest employee skill profiles
        </p>
      </div>

      {/* Query embedding box (top left of vector space) */}
      <div
        style={{
          position: "absolute",
          left: 100,
          top: 240,
          opacity: queryOpacity,
          transform: `scale(${queryScale})`,
          background: COLORS.midnightBlue,
          padding: "14px 24px",
          display: "flex",
          flexDirection: "column",
          gap: 4,
        }}
      >
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.turquoise,
            fontWeight: "bold",
          }}
        >
          ROLE QUERY EMBEDDING
        </span>
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            color: COLORS.white,
          }}
        >
          "Sr Data Engineer Data Engineering Python Spark Azure SQL"
        </span>
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.amethyst,
            marginTop: 4,
          }}
        >
          → text-embedding-3-small → 1536-dim vector
        </span>
      </div>

      {/* Vector space area */}
      <div
        style={{
          position: "absolute",
          left: 250,
          top: 300,
          width: 1050,
          height: 450,
        }}
      >
        {/* Axis labels */}
        <div
          style={{
            position: "absolute",
            left: -30,
            top: "50%",
            transform: "rotate(-90deg) translateX(-50%)",
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.grey,
          }}
        >
          Dimension 2
        </div>
        <div
          style={{
            position: "absolute",
            bottom: -30,
            left: "50%",
            transform: "translateX(-50%)",
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.grey,
          }}
        >
          Dimension 1
        </div>

        {/* Search radius circle */}
        {radiusProgress > 0 && (
          <div
            style={{
              position: "absolute",
              left: queryX - 250 - searchRadius,
              top: queryY - 300 - searchRadius,
              width: searchRadius * 2,
              height: searchRadius * 2,
              borderRadius: "50%",
              border: `2px dashed ${COLORS.trypanBlue}`,
              opacity: 0.4,
            }}
          />
        )}

        {/* Query point */}
        <GlowDot
          x={queryX - 250}
          y={queryY - 300}
          color={COLORS.rose}
          size={18}
          delay={50}
          pulse
        />
        {queryOpacity > 0.5 && (
          <div
            style={{
              position: "absolute",
              left: queryX - 250 + 14,
              top: queryY - 300 - 10,
              fontFamily: FONT.family,
              fontSize: FONT.small.size,
              fontWeight: "bold",
              color: COLORS.rose,
              opacity: queryOpacity,
            }}
          >
            Query
          </div>
        )}

        {/* Employee dots */}
        {EMPLOYEES.map((emp, i) => {
          const dotDelay = 60 + i * 3;
          const isNear = emp.highlight;
          const dotColor = isNear && highlightOpacity > 0.5
            ? COLORS.turquoise
            : COLORS.trypanBlue;
          const dotSize = isNear && highlightOpacity > 0.5 ? 14 : 8;

          return (
            <React.Fragment key={emp.id}>
              <GlowDot
                x={emp.x - 250}
                y={emp.y - 300}
                color={dotColor}
                size={dotSize}
                delay={dotDelay}
                pulse={isNear && highlightOpacity > 0.5}
              />
              {/* Labels for highlighted employees */}
              {isNear && resultOpacity > 0.5 && (
                <div
                  style={{
                    position: "absolute",
                    left: emp.x - 250 + 12,
                    top: emp.y - 300 - 8,
                    fontFamily: FONT.family,
                    fontSize: 12,
                    fontWeight: "bold",
                    color: COLORS.midnightBlue,
                    opacity: resultOpacity,
                  }}
                >
                  {emp.id} ({(emp.similarity * 100).toFixed(0)}%)
                </div>
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* ANN explanation */}
      <div
        style={{
          position: "absolute",
          right: 100,
          top: 240,
          opacity: annOpacity,
          background: COLORS.greyLight,
          border: `2px solid ${COLORS.emerald}`,
          padding: "16px 24px",
          width: 320,
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            fontWeight: "bold",
            color: COLORS.emerald,
            margin: "0 0 8px",
          }}
        >
          pgvector ANN Index
        </p>
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            color: COLORS.midnightBlue,
            margin: 0,
            lineHeight: 1.5,
          }}
        >
          IVFFlat index returns Top-K nearest employees in O(&#8730;N) — no full table scan needed
        </p>
      </div>

      {/* Bottom result summary */}
      <div
        style={{
          position: "absolute",
          bottom: 60,
          left: 250,
          opacity: resultOpacity,
          display: "flex",
          gap: 40,
          alignItems: "center",
        }}
      >
        <div
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.body.size,
            color: COLORS.midnightBlue,
          }}
        >
          Top 3 semantic matches:
        </div>
        {EMPLOYEES.filter(e => e.highlight).map(emp => (
          <div
            key={emp.id}
            style={{
              background: COLORS.turquoise,
              padding: "8px 16px",
              fontFamily: FONT.family,
              fontSize: FONT.caption.size,
              fontWeight: "bold",
              color: COLORS.midnightBlue,
            }}
          >
            {emp.id}: {(emp.similarity * 100).toFixed(0)}%
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
