# Design System Inspired by Apple, Reframed in Ocean Blue

## 1. Visual Theme & Atmosphere

This design system keeps the restraint, clarity, and product-first discipline of Apple-inspired interfaces, but replaces the stark black-and-white atmosphere with a calmer ocean-blue identity. The result should feel clean, precise, and immersive without becoming cold. The interface should communicate trust, clarity, and depth, making it suitable for a medical-adjacent product while still feeling premium.

Typography remains a structural anchor. San Francisco (SF Pro Display for large sizes, SF Pro Text for body) creates a precise and modern rhythm, especially when paired with tight headline line-heights and restrained weights. Headlines should still feel engineered rather than decorative, and body copy should remain highly readable across dense information layouts.

The color story now revolves around deep ocean surfaces, misted light backgrounds, and a single clear ocean-blue interaction accent. Instead of alternating between pure black and light gray, sections move between Deep Ocean (`#062B45`) and Sea Mist (`#EAF6FB`). Interactive elements center on Ocean Blue (`#0E7FB0`), with brighter aqua variants reserved for use on dark backgrounds. This creates a more atmospheric and domain-relevant identity while preserving the disciplined visual hierarchy of the original system.

**Key Characteristics:**
- SF Pro Display/Text with optical sizing for clear hierarchy
- Deep Ocean (`#062B45`) and Sea Mist (`#EAF6FB`) section rhythm instead of black and gray
- Ocean Blue (`#0E7FB0`) as the primary interaction and focus color
- Calm, premium surfaces with subtle blue undertones rather than neutral monochrome
- Extremely tight headline line-heights (1.07-1.14) for confident display typography
- Full-width section layout with centered content blocks
- Pill-shaped CTAs (980px radius) for soft, fluid actions
- Generous whitespace that makes each section feel like a distinct scene

## 2. Color Palette & Roles

### Primary
- **Deep Ocean** (`#062B45`): Hero backgrounds, immersive sections, navigation glass base.
- **Tide Blue** (`#0B5F89`): Secondary dark surface, supporting panels, strong section accents.
- **Sea Mist** (`#EAF6FB`): Light section backgrounds, informational blocks, spacious reading areas.
- **Foam White** (`#F7FCFF`): Clean elevated light surfaces and subtle contrast over Sea Mist.
- **Deep Slate** (`#102A43`): Primary text on light backgrounds, dark fills, high-legibility UI text.

### Interactive
- **Ocean Blue** (`#0E7FB0`): `--sk-focus-color`, primary CTA backgrounds, focus rings.
- **Reef Blue** (`#0A6A9C`): Inline links and secondary interactive text on light backgrounds.
- **Bright Aqua** (`#58C4E5`): Links and CTA outlines on dark backgrounds for stronger contrast.

### Text
- **Foam White** (`#F7FCFF`): Text on dark backgrounds, CTA text on dark/ocean fills.
- **Deep Slate** (`#102A43`): Primary body text on light backgrounds.
- **Slate 80%** (`rgba(16, 42, 67, 0.8)`): Secondary text, subdued UI text, metadata.
- **Slate 52%** (`rgba(16, 42, 67, 0.52)`): Tertiary text, disabled states, helper labels.

### Surface & Dark Variants
- **Ocean Surface 1** (`#10364F`): Card backgrounds in dark sections.
- **Ocean Surface 2** (`#0F3C58`): Subtle dark surface variation.
- **Ocean Surface 3** (`#124562`): Elevated cards on dark backgrounds.
- **Ocean Surface 4** (`#154C6C`): Highest dark surface elevation.
- **Ocean Surface 5** (`#0C3149`): Deepest supporting surface.

### Button States
- **Button Active** (`#D7EEF7`): Active or pressed state for light interactive elements.
- **Button Default Light** (`#F1F9FD`): Search and filter button backgrounds.
- **Overlay** (`rgba(12, 65, 96, 0.24)`): Media controls, image overlays, control scrims.
- **Foam 32%** (`rgba(247, 252, 255, 0.32)`): Hover state on dark modal close buttons.

### Shadows
- **Card Shadow** (`rgba(3, 36, 58, 0.18) 0px 12px 40px 0px`): Soft blue-tinted elevation for cards and floating panels.

## 3. Typography Rules

### Font Family
- **Display**: `SF Pro Display`, with fallbacks: `SF Pro Icons, Helvetica Neue, Helvetica, Arial, sans-serif`
- **Body**: `SF Pro Text`, with fallbacks: `SF Pro Icons, Helvetica Neue, Helvetica, Arial, sans-serif`
- SF Pro Display is used at 20px and above; SF Pro Text is optimized for 19px and below.

### Hierarchy

| Role | Font | Size | Weight | Line Height | Letter Spacing | Notes |
|------|------|------|--------|-------------|----------------|-------|
| Display Hero | SF Pro Display | 56px (3.50rem) | 600 | 1.07 (tight) | -0.28px | Maximum-impact headlines |
| Section Heading | SF Pro Display | 40px (2.50rem) | 600 | 1.10 (tight) | normal | Section titles |
| Tile Heading | SF Pro Display | 28px (1.75rem) | 400 | 1.14 (tight) | 0.196px | Card and tile headlines |
| Card Title | SF Pro Display | 21px (1.31rem) | 700 | 1.19 (tight) | 0.231px | Strong card headings |
| Sub-heading | SF Pro Display | 21px (1.31rem) | 400 | 1.19 (tight) | 0.231px | Regular card headings |
| Nav Heading | SF Pro Text | 34px (2.13rem) | 600 | 1.47 | -0.374px | Large navigation headings |
| Sub-nav | SF Pro Text | 24px (1.50rem) | 300 | 1.50 | normal | Light sub-navigation text |
| Body | SF Pro Text | 17px (1.06rem) | 400 | 1.47 | -0.374px | Standard reading text |
| Body Emphasis | SF Pro Text | 17px (1.06rem) | 600 | 1.24 (tight) | -0.374px | Emphasized labels and text |
| Button Large | SF Pro Text | 18px (1.13rem) | 300 | 1.00 (tight) | normal | Large button text |
| Button | SF Pro Text | 17px (1.06rem) | 400 | 2.41 (relaxed) | normal | Standard button text |
| Link | SF Pro Text | 14px (0.88rem) | 400 | 1.43 | -0.224px | Body links and secondary CTAs |
| Caption | SF Pro Text | 14px (0.88rem) | 400 | 1.29 (tight) | -0.224px | Secondary descriptions |
| Caption Bold | SF Pro Text | 14px (0.88rem) | 600 | 1.29 (tight) | -0.224px | Emphasized captions |
| Micro | SF Pro Text | 12px (0.75rem) | 400 | 1.33 | -0.12px | Fine print and helper text |
| Micro Bold | SF Pro Text | 12px (0.75rem) | 600 | 1.33 | -0.12px | Emphasized fine print |
| Nano | SF Pro Text | 10px (0.63rem) | 400 | 1.47 | -0.08px | Smallest legal or system text |

### Principles
- **Optical sizing as structure**: SF Pro automatically switches between Display and Text optical sizes. Use that transition intentionally rather than mixing display and text styles arbitrarily.
- **Weight restraint**: Most text should live at 400 and 600. Weight 300 should remain rare and decorative. Weight 700 should be used sparingly.
- **Negative tracking at all sizes**: Tight tracking creates a disciplined, efficient rhythm throughout the interface.
- **Extreme line-height range**: Headlines compress aggressively while body copy opens up for readability. This contrast creates hierarchy without adding noise.

## 4. Component Stylings

### Buttons

**Primary Ocean CTA**
- Background: `#0E7FB0` (Ocean Blue)
- Text: `#F7FCFF`
- Padding: 8px 15px
- Radius: 8px
- Border: 1px solid transparent
- Font: SF Pro Text, 17px, weight 400
- Hover: background brightens slightly toward `#1290C7`
- Active: `#D7EEF7` background shift for light contexts or slightly darker blue for dark contexts
- Focus: `2px solid var(--sk-focus-color, #0E7FB0)` outline
- Use: Primary call-to-action

**Primary Deep**
- Background: `#102A43`
- Text: `#F7FCFF`
- Padding: 8px 15px
- Radius: 8px
- Font: SF Pro Text, 17px, weight 400
- Use: Secondary CTA, dark variant

**Pill Link**
- Background: transparent
- Text: `#0A6A9C` (light bg) or `#58C4E5` (dark bg)
- Radius: 980px (full pill)
- Border: 1px solid currentColor
- Font: SF Pro Text, 14px-17px
- Hover: underline decoration or subtle tint fill
- Use: "Learn more", "View details", "Start diagnosis"

**Filter / Search Button**
- Background: `#F1F9FD`
- Text: `rgba(16, 42, 67, 0.8)`
- Padding: 0px 14px
- Radius: 11px
- Border: 3px solid `rgba(14, 127, 176, 0.08)`
- Focus: `2px solid var(--sk-focus-color, #0E7FB0)` outline
- Use: Search bars, filter controls

**Media Control**
- Background: `rgba(12, 65, 96, 0.24)`
- Text: `rgba(247, 252, 255, 0.88)` on dark media, `rgba(16, 42, 67, 0.6)` on light media
- Radius: 50% (circular)
- Active: scale(0.9), background shifts
- Focus: `2px solid var(--sk-focus-color, #0E7FB0)` outline
- Use: Play/pause, carousel arrows, image controls

### Cards & Containers
- Background: `#F7FCFF` or `#EAF6FB` in light contexts, `#10364F`-`#154C6C` in dark contexts
- Border: none or a very subtle `1px` tint when separation is needed
- Radius: 5px-8px for standard surfaces, 12px for richer panels
- Shadow: `rgba(3, 36, 58, 0.18) 0px 12px 40px 0px` for elevated cards
- Content: centered or left-aligned depending on density, with generous padding
- Hover: restrained; avoid loud lifting animations

### Navigation
- Background: `rgba(6, 43, 69, 0.78)` with `backdrop-filter: saturate(180%) blur(20px)`
- Height: 48px
- Text: `#F7FCFF` at 12px, weight 400
- Active: underline or subtle color shift on hover
- Logo: simple brand mark or wordmark, centered or left-aligned
- Mobile: collapses to hamburger with full-screen overlay menu
- The nav should float above content and retain its ocean-glass identity regardless of section background

### Image Treatment
- Use solid or softly tinted ocean-adjacent backgrounds rather than stark black fields
- Full-bleed section imagery should feel clean, spacious, and uncluttered
- Product or illustrative imagery should remain sharply presented with subtle, realistic shadowing
- Lifestyle or contextual imagery should sit inside rounded containers (12px+ radius) when used

### Distinctive Components

**Hero Module**
- Full-viewport-width section with a solid Deep Ocean or Sea Mist background
- Primary headline at 56px SF Pro Display, weight 600
- One-line descriptor below in lighter weight
- Two CTAs side by side: outline pill + filled primary button

**Information Tile**
- Square or near-square card on a contrasting background
- Primary visual or icon occupying 50-70% of the tile
- Title and short supporting description below
- Secondary action links at the bottom

**Comparison Strip**
- Horizontal scroll of variants, options, or diagnosis summaries
- Each item presented as a vertical card with a clear title and key facts
- Minimal chrome; content clarity comes first

## 5. Layout Principles

### Spacing System
- Base unit: 8px
- Scale: 2px, 4px, 5px, 6px, 7px, 8px, 9px, 10px, 11px, 14px, 15px, 17px, 20px, 24px
- The scale is dense at small sizes and more spacious at larger sizes, allowing precise control over typography and interface alignment.

### Grid & Container
- Max content width: approximately 980px
- Hero sections: full-viewport-width with centered content blocks
- Content grids: 2-3 columns within a centered container
- Single-column layouts for major moments or focused information
- Structure should be implied by spacing, not by visible scaffolding

### Whitespace Philosophy
- **Cinematic breathing room**: Important sections should feel spacious and intentional.
- **Vertical rhythm through ocean color blocks**: Alternate Deep Ocean and Sea Mist sections to create scene changes without heavy separators.
- **Compression within, expansion between**: Text remains tightly set while surrounding whitespace stays generous.

### Border Radius Scale
- Micro (5px): Small containers, tags, compact surfaces
- Standard (8px): Buttons, cards, image containers
- Comfortable (11px): Search inputs, filter controls
- Large (12px): Feature panels, modal media containers
- Full Pill (980px): CTA links and navigation pills
- Circle (50%): Media controls and icon buttons

## 6. Depth & Elevation

| Level | Treatment | Use |
|-------|-----------|-----|
| Flat (Level 0) | No shadow, solid background | Standard content sections, text blocks |
| Navigation Glass | `backdrop-filter: saturate(180%) blur(20px)` on `rgba(6, 43, 69, 0.78)` | Sticky navigation bar |
| Subtle Lift (Level 1) | `rgba(3, 36, 58, 0.18) 0px 12px 40px 0px` | Cards, floating panels |
| Media Control | `rgba(12, 65, 96, 0.24)` background with scale transforms | Play/pause buttons, carousel controls |
| Focus (Accessibility) | `2px solid #0E7FB0` outline | Keyboard focus on all interactive elements |

**Shadow Philosophy**: Use shadow sparingly. Elevation should come mainly from tonal contrast between ocean surfaces rather than heavy drop shadows. When shadows appear, they should feel soft, cool, and diffused rather than dramatic.

### Decorative Depth
- Navigation glass is the most recognizable depth element and should remain subtle but present
- Section color transitions should carry much of the perceived depth between content blocks
- Imagery can include natural shadowing, but the UI should avoid synthetic excess

## 7. Do's and Don'ts

### Do
- Use SF Pro Display at 20px+ and SF Pro Text below 20px
- Apply negative letter-spacing at all text sizes where the system calls for it
- Use Ocean Blue (`#0E7FB0`) as the primary interaction color
- Alternate between Deep Ocean (`#062B45`) and Sea Mist (`#EAF6FB`) section backgrounds
- Use 980px pill radius for pill CTAs and soft navigation actions
- Keep imagery on clean, controlled color fields
- Use translucent ocean glass for sticky navigation
- Compress headline line-heights to 1.07-1.14 for display moments

### Don't
- Don't introduce unrelated accent colors that compete with the ocean-blue system
- Don't use heavy shadows or stacked shadow layers
- Don't rely on hard black-and-white contrast as the default visual rhythm
- Don't apply wide letter-spacing to SF Pro
- Don't use weight 800 or 900
- Don't add noisy textures or visual clutter to key backgrounds
- Don't make the navigation opaque unless a task specifically requires it
- Don't center-align long body copy
- Don't use oversized corner radii on standard rectangular surfaces

## 8. Responsive Behavior

### Breakpoints
| Name | Width | Key Changes |
|------|-------|-------------|
| Small Mobile | <360px | Minimum supported, single column |
| Mobile | 360-480px | Standard mobile layout |
| Mobile Large | 480-640px | Wider single column, larger imagery |
| Tablet Small | 640-834px | 2-column grids begin |
| Tablet | 834-1024px | Full tablet layout, expanded nav |
| Desktop Small | 1024-1070px | Standard desktop layout begins |
| Desktop | 1070-1440px | Full layout, max content width |
| Large Desktop | >1440px | Centered with generous margins |

### Touch Targets
- Primary CTAs: padding should yield roughly 44px touch height
- Navigation links: 48px height with adequate spacing
- Media controls: minimum 44x44px
- Pill links: generous padding for comfortable tapping

### Collapsing Strategy
- Hero headlines: 56px Display → 40px → 28px on mobile, maintaining tight line-height proportionally
- Grids: 3-column → 2-column → single column stacked
- Navigation: full horizontal nav → compact mobile menu
- Hero modules: full-bleed feel maintained at all sizes, with text scaling down gracefully
- Section backgrounds: preserve full-width ocean color blocks at every breakpoint
- Images: scale proportionally and preserve their core silhouette or subject clarity

### Image Behavior
- Maintain aspect ratio at all breakpoints
- Keep hero imagery centered
- Preserve full-bleed section backgrounds where they reinforce the layout
- Contextual imagery may crop on mobile if composition remains strong
- Lazy load below-the-fold images

## 9. Agent Prompt Guide

### Quick Color Reference
- Primary CTA: Ocean Blue (`#0E7FB0`)
- Page background (light): `#EAF6FB`
- Page background (light elevated): `#F7FCFF`
- Page background (dark): `#062B45`
- Secondary dark surface: `#0B5F89`
- Heading text (light): `#102A43`
- Heading text (dark): `#F7FCFF`
- Body text: `rgba(16, 42, 67, 0.8)` on light, `#F7FCFF` on dark
- Link (light bg): `#0A6A9C`
- Link (dark bg): `#58C4E5`
- Focus ring: `#0E7FB0`
- Card shadow: `rgba(3, 36, 58, 0.18) 0px 12px 40px 0px`

### Example Component Prompts
- "Create a hero section on a Deep Ocean background. Headline at 56px SF Pro Display weight 600, line-height 1.07, letter-spacing -0.28px, color Foam White. One-line subtitle at 21px SF Pro Display weight 400, line-height 1.19, color Foam White. Two CTAs: 'Learn more' as an outline pill and 'Start diagnosis' as a filled Ocean Blue button."
- "Design an information card with a Sea Mist background, 8px border-radius, subtle blue-tinted shadow, and a clean top visual area. Title at 28px SF Pro Display weight 400, description at 14px SF Pro Text weight 400 in rgba(16,42,67,0.8), and action links in Reef Blue."
- "Build a sticky navigation bar with an ocean-glass background: rgba(6,43,69,0.78) plus backdrop blur. Links at 12px SF Pro Text weight 400, Foam White text, simple brand mark left, actions right."
- "Create an alternating section layout: first section Deep Ocean with Foam White text and centered imagery, second section Sea Mist with Deep Slate text. Each section should feel near full-viewport height."
- "Design a pill CTA link with Reef Blue on light backgrounds or Bright Aqua on dark backgrounds, 14px SF Pro Text, 980px radius, and underline on hover."

### Iteration Guide
1. Ocean Blue (`#0E7FB0`) is the primary interaction color and should remain dominant across interactive states.
2. Section backgrounds should alternate between Deep Ocean and Sea Mist to create calm visual pacing.
3. Typography optical sizing still matters: SF Pro Display at 20px+, SF Pro Text below.
4. Tight tracking remains part of the system and should not be loosened casually.
5. The ocean-glass navigation treatment is a defining UI signature.
6. Key visuals should live on clean color fields, not noisy or cluttered backgrounds.
7. Elevation should be soft, cool, and restrained.
8. Pill CTAs should keep their fluid, capsule-like shape through the 980px radius pattern.
