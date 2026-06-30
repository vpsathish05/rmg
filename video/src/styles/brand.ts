// Jman Brand Constants — from SKILL.md

export const COLORS = {
  // Primary
  midnightBlue: "#19105B",
  trypanBlue: "#3411A3",

  // Secondary
  rose: "#FF6196",
  turquoise: "#71EAE1",
  lightBlue: "#26D4F0",
  amethyst: "#A16BDB",

  // Tertiary
  berry: "#A6265E",
  emerald: "#16978E",
  grey: "#D9D9D9",
  greyLight: "#F2F2F2",

  // RAG
  red: "#FF0000",
  amber: "#FFC000",
  green: "#00B050",

  // Basics
  white: "#FFFFFF",
  black: "#000000",
} as const;

export const FONT = {
  family: "Arial, sans-serif",
  heading: { size: 48, weight: "bold" as const },
  subheading: { size: 32, weight: "normal" as const },
  body: { size: 24, weight: "normal" as const },
  caption: { size: 18, weight: "normal" as const },
  small: { size: 14, weight: "normal" as const },
} as const;

// Scene durations in frames (30fps)
export const SCENES = {
  title: { start: 0, duration: 90 },         // 3s
  input: { start: 90, duration: 210 },        // 7s
  coe: { start: 300, duration: 240 },         // 8s
  semantic: { start: 540, duration: 300 },     // 10s
  formula: { start: 840, duration: 360 },      // 12s
  enrichment: { start: 1200, duration: 300 },  // 10s
  output: { start: 1500, duration: 300 },      // 10s
} as const;
