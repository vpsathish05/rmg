---
name: jman-formatting
description: JMAN brand formatting rules for AI Play Book content. Use when creating or reviewing any MDX article, mermaid diagram, or visual content.
---

# JMAN Formatting Rules

## Colours

### Primary (use first, in order)
- Midnight Blue: #19105B (rgb 25,16,91) - headings, text on light backgrounds, primary fills
- Trypan Blue: #3411A3 (rgb 52,17,163) - accent, links, secondary fills

### Secondary (sparingly, for highlights only)
- Rose: #FF6196 (rgb 255,97,150)
- Turquoise: #71EAE1 (rgb 113,234,225) - only colour where text should be Midnight Blue, not white
- Light Blue: #26D4F0 (rgb 38,212,240)
- Amethyst: #A16BDB (rgb 161,107,219)

### Tertiary
- Berry: #A6265E (rgb 166,38,94)
- Emerald: #16978E (rgb 22,151,142)
- Grey: #D9D9D9 / #F2F2F2 (backgrounds, borders)

### RAG (status indicators)
- Red: #FF0000 - bad/down
- Amber: #FFC000 - warning
- Green: #00B050 - good/up

### Colour Rules
- 75% white, 20% primary, 5% secondary - never let secondary overpower primary
- White text on all coloured backgrounds EXCEPT turquoise (use Midnight Blue)
- Use colours left to right through the palette when adding new elements
- Text on light backgrounds: always Midnight Blue

## Typography

- Typeface: Arial
- Headings: Arial Bold, 23pt equivalent
- Subheadings: Arial, 16pt equivalent
- Body: Arial, 12pt equivalent (never exceed 12, never below 8)
- Source/caption: Arial Italic, 8pt equivalent
- All text colour: Midnight Blue on light backgrounds, White on dark backgrounds

## Mermaid Diagram Rules

Apply these classDef styles in every mermaid diagram:

```
classDef primary fill:#3411A3,stroke:#19105B,color:#FFFFFF
classDef secondary fill:#F2F2F2,stroke:#D9D9D9,color:#19105B
classDef accent fill:#71EAE1,stroke:#16978E,color:#19105B
classDef highlight fill:#FF6196,stroke:#A6265E,color:#FFFFFF
```

### Node styling
- Main process/service nodes: primary (Trypan Blue fill, white text)
- Input/output/external nodes: secondary (Grey fill, Midnight Blue text)
- Key highlight nodes: accent (Turquoise fill, Midnight Blue text)
- Warning/attention nodes: highlight (Rose fill, white text)

### Diagram rules
- Shapes: square corners only (no rounded)
- Lines: 1pt weight
- Line colours: Midnight Blue, Trypan Blue, or Rose only
- Dashed lines: Midnight Blue only
- Subgraph borders: Trypan Blue or Grey, no fill

## Shapes and Boxes

- All shapes: square corners (no rounded corners ever)
- Shapes: either outlined (1pt stroke) or filled - never both
- Filled shapes: text in white or Midnight Blue only
- No tints outside the permitted colour range

## Call-out Boxes (Blockquotes in MDX)

- Use for highlighting key information
- Background: Rose (secondary colour, first choice for callouts)
- Text: White on coloured callout backgrounds
- Keep to single key statement where possible

## Tables

- Header row: Midnight Blue background, white text, bold
- Row separators: Rose (1pt line)
- Body text: Midnight Blue
- First column (row headers): Bold
- Alternating row backgrounds: not required (white is fine)

## Charts/Diagrams Colour Order

When multiple series or categories appear:
1. Midnight Blue
2. Trypan Blue
3. Rose
4. Turquoise

Use tints of primary colours for additional series. Use a secondary colour only to highlight a specific data point.

## Lines

- All lines: 1pt weight
- Solid lines: Midnight Blue or Trypan Blue
- Accent lines (separators): Rose
- Dashed lines: Midnight Blue only, regular dash

## Arrows

- No auto-shape arrows
- Arrow = isosceles triangle, height is 1/8 of base
- Large arrows (base > 3cm): use lighter colour (Rose or Turquoise)
- Small arrows: Midnight Blue

## Kicker / Key Takeaway

- Single line emphasis at end of a section
- Use secondary highlight colour (Rose background, white text)
- Keep to one sentence

## What NOT to Do

- No rounded corners on any shape
- No colours outside the defined palette
- No gradients in MDX (gradients go bottom-left to top-right, dark to light - for presentations only)
- No text smaller than 8pt equivalent
- No secondary colours as large blocks - they are highlights only
- No auto-shape arrows
- Never use turquoise background with white text (use Midnight Blue text instead)
