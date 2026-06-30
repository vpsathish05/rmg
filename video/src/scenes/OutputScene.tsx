import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, spring, useVideoConfig } from "remotion";
import { COLORS, FONT } from "../styles/brand";
import { BrandLogo } from "../components/BrandLogo";

const CANDIDATES = [
  { id: "EMP_042", role: "Sr Data Engineer", location: "India", category: "Available", score: 84, avail: "100%" },
  { id: "EMP_015", role: "Solutions Enabler", location: "India", category: "Available", score: 76, avail: "80%" },
  { id: "EMP_088", role: "Sr Software Engineer", location: "UK", category: "BestMatch", score: 71, avail: "30%" },
];

export const OutputScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Title
  const titleOpacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Card header
  const headerScale = spring({
    frame: frame - 20,
    fps,
    config: { damping: 14, stiffness: 100 },
  });
  const headerOpacity = interpolate(frame, [20, 35], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Candidate rows
  const getRowOpacity = (i: number) =>
    interpolate(frame, [50 + i * 25, 65 + i * 25], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  const getRowX = (i: number) =>
    interpolate(frame, [50 + i * 25, 65 + i * 25], [-30, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });

  // Rationale box
  const rationaleOpacity = interpolate(frame, [140, 165], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // KB proof badge
  const kbOpacity = interpolate(frame, [175, 195], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Hire signal (or end branding)
  const endOpacity = interpolate(frame, [220, 250], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Final logo
  const logoDelay = 260;

  return (
    <AbsoluteFill
      style={{
        background: COLORS.midnightBlue,
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
          OUTPUT
        </p>
        <h2
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.heading.size,
            fontWeight: "bold",
            color: COLORS.white,
            margin: "8px 0 0",
          }}
        >
          Final Recommendation
        </h2>
      </div>

      {/* Recommendation Card */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 200,
          width: 1000,
          background: COLORS.white,
          overflow: "hidden",
          opacity: headerOpacity,
          transform: `scale(${headerScale})`,
        }}
      >
        {/* Card header */}
        <div
          style={{
            background: COLORS.trypanBlue,
            padding: "16px 28px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <div>
            <span
              style={{
                fontFamily: FONT.family,
                fontSize: FONT.body.size,
                fontWeight: "bold",
                color: COLORS.white,
              }}
            >
              Senior Data Engineer — Sigma Healthcare
            </span>
          </div>
          <div
            style={{
              background: "rgba(255,255,255,0.15)",
              border: "1px solid rgba(255,255,255,0.3)",
              padding: "4px 14px",
            }}
          >
            <span
              style={{
                fontFamily: FONT.family,
                fontSize: FONT.small.size,
                fontWeight: "bold",
                color: COLORS.turquoise,
              }}
            >
              Data Engineering
            </span>
          </div>
        </div>

        {/* Table header */}
        <div
          style={{
            display: "flex",
            padding: "12px 28px",
            background: COLORS.greyLight,
            borderBottom: `1px solid ${COLORS.grey}`,
          }}
        >
          {["Employee", "Role", "Location", "Category", "Available", "Score"].map((h) => (
            <span
              key={h}
              style={{
                flex: h === "Employee" ? 1.2 : h === "Role" ? 1.5 : 1,
                fontFamily: FONT.family,
                fontSize: 13,
                fontWeight: "bold",
                color: COLORS.midnightBlue,
                textTransform: "uppercase",
                letterSpacing: 1,
              }}
            >
              {h}
            </span>
          ))}
        </div>

        {/* Candidate rows */}
        {CANDIDATES.map((c, i) => (
          <div
            key={c.id}
            style={{
              display: "flex",
              padding: "14px 28px",
              borderBottom: i < CANDIDATES.length - 1 ? `1px solid ${COLORS.greyLight}` : "none",
              alignItems: "center",
              opacity: getRowOpacity(i),
              transform: `translateX(${getRowX(i)}px)`,
            }}
          >
            <span
              style={{
                flex: 1.2,
                fontFamily: FONT.family,
                fontSize: FONT.caption.size,
                fontWeight: "bold",
                color: COLORS.midnightBlue,
              }}
            >
              {c.id}
            </span>
            <span
              style={{
                flex: 1.5,
                fontFamily: FONT.family,
                fontSize: FONT.caption.size,
                color: COLORS.midnightBlue,
              }}
            >
              {c.role}
            </span>
            <span
              style={{
                flex: 1,
                fontFamily: FONT.family,
                fontSize: FONT.caption.size,
                color: COLORS.midnightBlue,
              }}
            >
              {c.location}
            </span>
            <span
              style={{
                flex: 1,
                fontFamily: FONT.family,
                fontSize: FONT.small.size,
                fontWeight: "bold",
                color: c.category === "Available" ? COLORS.green : COLORS.trypanBlue,
              }}
            >
              {c.category}
            </span>
            <span
              style={{
                flex: 1,
                fontFamily: FONT.family,
                fontSize: FONT.caption.size,
                color: COLORS.midnightBlue,
              }}
            >
              {c.avail}
            </span>
            <span
              style={{
                flex: 1,
                fontFamily: FONT.family,
                fontSize: FONT.body.size,
                fontWeight: "bold",
                color: COLORS.midnightBlue,
              }}
            >
              {c.score}%
            </span>
          </div>
        ))}
      </div>

      {/* Rationale */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 590,
          width: 1000,
          opacity: rationaleOpacity,
          background: "rgba(255,255,255,0.05)",
          border: `1px solid rgba(255,255,255,0.15)`,
          padding: "16px 28px",
        }}
      >
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.small.size,
            fontWeight: "bold",
            color: COLORS.turquoise,
            margin: "0 0 6px",
            textTransform: "uppercase",
            letterSpacing: 1,
          }}
        >
          AI Rationale — #1 EMP_042
        </p>
        <p
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            color: COLORS.white,
            margin: 0,
            lineHeight: 1.6,
            opacity: 0.9,
          }}
        >
          Strong Spark and Python skills with 87% semantic match. Currently 100% available with proven delivery
          on similar Data Engineering projects for healthcare clients. Recommended as top pick.
        </p>
      </div>

      {/* KB Proof badge */}
      <div
        style={{
          position: "absolute",
          left: 120,
          top: 710,
          opacity: kbOpacity,
          display: "flex",
          alignItems: "center",
          gap: 12,
        }}
      >
        <div
          style={{
            background: COLORS.emerald,
            padding: "8px 16px",
          }}
        >
          <span
            style={{
              fontFamily: FONT.family,
              fontSize: FONT.small.size,
              fontWeight: "bold",
              color: COLORS.white,
            }}
          >
            KB PROOF
          </span>
        </div>
        <span
          style={{
            fontFamily: FONT.family,
            fontSize: FONT.caption.size,
            color: COLORS.white,
            opacity: 0.7,
          }}
        >
          PROJECT_089 (Sigma, Data Eng) — 92% similarity match
        </span>
      </div>

      {/* End: Stats + logo */}
      <div
        style={{
          position: "absolute",
          right: 120,
          top: 250,
          opacity: endOpacity,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 20,
        }}
      >
        {/* Stats */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            gap: 12,
            alignItems: "center",
          }}
        >
          {[
            { label: "Evaluated", value: "187" },
            { label: "Available", value: "2" },
            { label: "BestMatch", value: "1" },
          ].map((s) => (
            <div key={s.label} style={{ textAlign: "center" }}>
              <p
                style={{
                  fontFamily: FONT.family,
                  fontSize: 36,
                  fontWeight: "bold",
                  color: COLORS.white,
                  margin: 0,
                }}
              >
                {s.value}
              </p>
              <p
                style={{
                  fontFamily: FONT.family,
                  fontSize: FONT.small.size,
                  color: COLORS.turquoise,
                  margin: 0,
                  textTransform: "uppercase",
                  letterSpacing: 1,
                }}
              >
                {s.label}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Final brand */}
      <div
        style={{
          position: "absolute",
          bottom: 50,
          right: 120,
          opacity: endOpacity,
          display: "flex",
          alignItems: "center",
          gap: 16,
        }}
      >
        <BrandLogo size={48} delay={logoDelay} />
        <div>
          <p
            style={{
              fontFamily: FONT.family,
              fontSize: FONT.body.size,
              fontWeight: "bold",
              color: COLORS.white,
              margin: 0,
            }}
          >
            RMG Engine
          </p>
          <p
            style={{
              fontFamily: FONT.family,
              fontSize: FONT.small.size,
              color: COLORS.white,
              opacity: 0.5,
              margin: 0,
            }}
          >
            Jman Group
          </p>
        </div>
      </div>
    </AbsoluteFill>
  );
};
