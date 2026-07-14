# Hongyu Ding Academic Homepage — Design Specification

**Date:** 2026-07-14  
**Status:** User-approved design; awaiting written-spec review  
**Target:** A production-ready, static academic homepage for Hongyu Ding

## 1. Purpose

Build a concise academic homepage that presents Hongyu Ding’s research agenda, recent activity, representative work, complete current publication list, and contact paths. The page should be credible to robotics and embodied-AI researchers while remaining readable to visitors outside the exact subfield.

The design uses the information hierarchy of Danfei Xu and Jon Barron as a starting point, but it does not copy their legacy implementation. Project entries adopt Hang Zhao-style plain-language contribution summaries and Shuran Song-style visual publication rows.

## 2. Success Criteria

The finished homepage must:

1. Establish identity, affiliation, and research direction within the first viewport.
2. Expose Email, Google Scholar, and GitHub without menu traversal.
3. Show exactly five recent, verifiable News items.
4. Explain three research themes before listing papers.
5. Present three selected publications with real media, accurate metadata, one-sentence summaries, and only verified resource links.
6. Present the current complete publication set in a compact year-grouped list.
7. Include an honest Academic Service state without inventing roles.
8. Reflow cleanly at 375, 768, 1280, and 1920 px with no horizontal scrolling.
9. Remain fully readable without JavaScript.
10. Avoid generic startup styling, decorative technology motifs, unsupported claims, and generated research imagery.

## 3. Confirmed Public Identity

- **Name:** Hongyu Ding
- **Role:** PhD Student at Nanjing University
- **Email:** `hongyuding@smail.nju.edu.cn`
- **Google Scholar:** `https://scholar.google.com/citations?user=IvWH8tcAAAAJ`
- **GitHub:** `https://github.com/Darkness-hy`
- **CV:** Omitted from the first release
- **Scholar-listed interests:** Embodied AI, Robotics, Reinforcement Learning

### Hero research thesis

> I study embodied intelligence, focusing on how language, vision, and robot actions can be translated into unified navigation and decision-making systems.

### Introductory biography

The first-release biography should use this restrained draft:

> I am a PhD student at Nanjing University. My research lies at the intersection of embodied AI, robotics, and reinforcement learning. I study how language, vision, and robot actions can be translated into unified navigation and decision-making systems, with a focus on training-free adaptation, zero-shot generalization, and structured learning signals for agents operating in continuous environments.

The biography must remain factual and may be edited later without changing the page structure.

## 4. Scope

### Included

- Profile and portrait
- One-line identity and research thesis
- Short biography
- Email / Scholar / GitHub links
- Five News entries
- Research themes
- Three Selected Publications
- Complete current Publications
- Academic Service
- Minimal footer with last-updated date

### Excluded

- CV link
- Separate Awards page
- Teaching page
- Mentorship page
- Citation counters
- Media carousel
- Lab-member page
- Recruiting panel
- Talks section
- Social feed
- Dark theme
- Publication filters
- Decorative animation
- Generated or stock robotics imagery

## 5. Visual Direction

### Concept

**Evidence-Led Editorial:** a warm, paper-like academic page whose distinction comes from typography, spacing, the supplied portrait, and real research visuals. It should feel personal and authored, but not branded like a startup or styled like a generic portfolio template.

### Color tokens

```css
--color-paper: #f6f2e9;
--color-surface: #fbf9f4;
--color-ink: #202522;
--color-muted: #5f6863;
--color-accent: #8f4636;
--color-line: #d8d1c5;
--color-highlight: #eee3d8;
--color-focus: #2d5f85;
```

Rules:

- Use `--color-paper` as the page background.
- Use `--color-ink` for primary text.
- Use `--color-accent` only for links, small section markers, and restrained emphasis.
- Links must not depend on color alone; use underlines or border transitions.
- Do not add a second decorative accent color.

### Typography

- **Display / headings:** Newsreader variable serif.
- **Body / metadata / links:** IBM Plex Sans.
- Self-host WOFF2 files from official open-source releases.
- Font fallbacks:
  - Newsreader → Georgia → serif.
  - IBM Plex Sans → system sans-serif.

Recommended desktop sizes:

- Name: `clamp(3rem, 7vw, 5.4rem)` with restrained line-height.
- Section headings: `clamp(1.8rem, 3vw, 2.5rem)`.
- Body: `1rem` to `1.0625rem`, line-height approximately `1.65`.
- Publication title: `1.15rem` to `1.3rem`, semibold.
- Metadata: `0.875rem` to `0.9375rem`.

### Decoration

Allowed:

- Thin rules
- Small numeric section markers
- Warm neutral publication highlights
- Subtle image corner radius
- Visible text-link hover and focus states

Not allowed:

- Card shadows
- Glassmorphism
- Neon gradients
- Glow
- Circuit or HUD motifs
- Parallax
- Autoplay hero video
- Hover-only paper previews
- Large badge systems

## 6. Layout

### Global container

- Maximum content width: `940px`.
- Horizontal padding: `24px` desktop/tablet and `18px` mobile.
- Center the page with automatic margins.
- Use semantic HTML landmarks: `header`, `main`, `section`, `article`, and `footer`.
- Do not use layout tables or custom presentational elements.

### Profile / hero

Desktop:

- Two-column CSS Grid, approximately `2fr 1fr`.
- Text appears first in source order.
- Portrait occupies roughly 280–310 px width.
- Contact links appear directly below the biography.

Mobile below approximately `700px`:

- Single column.
- Name, role, thesis, biography, and links appear before the portrait.
- The portrait remains large enough to be recognizable but does not dominate the first screen.

### Section rhythm

Order:

1. Profile
2. News
3. Research
4. Selected Publications
5. Publications
6. Academic Service
7. Footer

Use generous section spacing and a thin rule between major sections. Do not add a large navigation bar. The section order and headings provide sufficient orientation for the first-release page length.

## 7. Portrait

### Source

`figs/ChatGPT Image 2026年6月29日 16_41_32.png`

The source must remain untouched.

### Output

Create:

- `assets/images/profile-hongyu-ding.webp`, 720 × 900 px.

Recommended crop from the 1118 × 1407 source:

- Approximate source rectangle: `x=199`, `y=430`, `width=720`, `height=900`.

The final crop must retain the hairline, glasses, ears, chin, shoulders, and enough architecture to preserve the photograph’s character. It must not use a circular mask, artificial bokeh, skin smoothing, background replacement, or cinematic grading.

Use alt text: `Portrait of Hongyu Ding.`

## 8. News

Render exactly five reverse-chronological entries as a two-column date/content list on desktop and a stacked list on mobile.

First-release copy:

1. **May 2026** — Released Uni-LaViRA, a training-free framework for unified embodied navigation, with a paper, project page, and code.
2. **March 2026** — Updated LaViRA with its ICRA 2026 version for zero-shot vision-language navigation in continuous environments.
3. **October 2025** — Released LaViRA with its paper, project page, and code.
4. **December 2023** — Magnetic Field-Based Reward Shaping appeared in IEEE/CAA Journal of Automatica Sinica, volume 10, issue 12.
5. **July 2023** — Magnetic Field-Based Reward Shaping became available online with project, code, and supplementary-video resources.

Each entry may link its publication or project title. Do not turn the entries into cards or add unverified awards, rankings, citation counts, or acceptance claims beyond the stated metadata.

## 9. Research

Present three numbered themes in a three-column editorial grid on wide screens and a single column on narrow screens. Use rules and spacing rather than cards.

### 01 — Language–Vision–Action Translation

Study how knowledge expressed through language and visual representations can be translated into robot actions without retraining a separate policy for every task.

Associated work: Uni-LaViRA and LaViRA.

### 02 — Unified Embodied Navigation

Develop interfaces that let embodied agents address multiple navigation settings and continuous environments through a shared action-translation perspective.

Associated work: Uni-LaViRA and LaViRA.

### 03 — Goal-Conditioned Reinforcement Learning

Design structured learning signals that improve exploration and decision-making when rewards are sparse and goals vary across episodes.

Associated work: Magnetic Field-Based Reward Shaping.

## 10. Selected Publications

### Shared publication anatomy

Every selected-paper `article` must contain:

1. Real teaser or demo frame
2. Linked paper title
3. Full ordered author list with `Hongyu Ding` emphasized
4. Venue and year
5. One-sentence plain-language contribution summary
6. Literal resource labels, shown only when a verified URL exists

Desktop layout: approximately `220px 1fr`.  
Mobile layout: media above text.

Do not autoplay video. Teasers must come from the official project page, paper, or author-controlled repository. If a suitable image cannot be obtained, render a text-only article without an empty placeholder.

### Uni-LaViRA

**Title:** Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified Embodied Navigation

**Authors:** Hongyu Ding, Sizhuo Zhang, Ziming Xu, Jinwen Guo, Hongxiu Liu, Xingzhi Cheng, Zixuan Chen, Haifei Qi, Duo Wang, Hao Xu, Jieqi Shi, Yifan Zhang, Jing Huo, Jian Cheng, Yang Gao, Jiebo Luo

**Status:** arXiv preprint, 2026

**Summary:** Training-free unified embodied navigation through language–vision–robot action translation.

**Links:**

- Paper: `https://arxiv.org/abs/2605.27582`
- Project: `https://xetroubadour.github.io/Uni-LaViRA/`
- Code: `https://github.com/NJU-R-L-Group-Embodied-Lab/uni-lavira-code`

Do not show Video or Dataset in the first release.

### LaViRA

**Title:** LaViRA: Language-Vision-Robot Actions Translation for Zero-Shot Vision Language Navigation in Continuous Environments

**Authors:** Hongyu Ding, Ziming Xu, Yudong Fang, You Wu, Zixuan Chen, Jieqi Shi, Jing Huo, Yifan Zhang, Yang Gao

**Status:** ICRA 2026

**Summary:** Zero-shot continuous navigation through language–vision–robot action translation.

**Links:**

- Paper: `https://arxiv.org/abs/2510.19655`
- Project: `https://robo-lavira.github.io/lavira-zs-vln/`
- Code: `https://github.com/NJU-R-L-Group-Embodied-Lab/lavira-code`

Do not show Video or Dataset in the first release.

### Magnetic Field-Based Reward Shaping

**Title:** Magnetic Field-Based Reward Shaping for Goal-Conditioned Reinforcement Learning

**Authors:** Hongyu Ding, Yuanze Tang, Qing Wu, Bo Wang, Chunlin Chen, Zhi Wang

**Venue:** IEEE/CAA Journal of Automatica Sinica, 10(12):2233–2247, 2023

**Summary:** Magnetic-field-inspired rewards for efficient goal-conditioned reinforcement learning.

**Links:**

- Paper: `https://doi.org/10.1109/JAS.2023.123477`
- Project: `https://hongyuding.wixsite.com/mfrs`
- Code: `https://github.com/Darkness-hy/mfrs`
- Video: `https://www.bilibili.com/video/BV1784y1z7Bj`

Do not show Dataset in the first release.

## 11. Complete Publications

Render the same current three records as compact citations grouped by year:

### 2026

- Uni-LaViRA
- LaViRA

### 2023

- Magnetic Field-Based Reward Shaping

The compact list may repeat titles already shown above because its purpose differs: Selected Publications explains contributions; Publications provides a complete, copyable bibliography. Include paper links but omit teaser images and contribution summaries in the compact list.

## 12. Academic Service

Render:

> Details coming soon.

Do not infer reviewing, committee, teaching, mentoring, or organization roles from affiliations or publications.

## 13. Footer and Metadata

Footer content:

- `© 2026 Hongyu Ding`
- `Last updated July 2026`

Document metadata:

- Page title: `Hongyu Ding — Embodied AI, Robotics, and Reinforcement Learning`
- Description: `Hongyu Ding is a PhD student at Nanjing University working on embodied intelligence, language–vision–action translation, navigation, and reinforcement learning.`
- Open Graph title and description matching the page metadata
- Open Graph portrait image using the exported profile image

Do not add a canonical URL until a deployment domain is known. Do not write a fake domain or placeholder URL into the page.

## 14. File Structure

```text
index.html
assets/
├── css/
│   └── site.css
├── fonts/
│   ├── newsreader-variable.woff2
│   ├── ibm-plex-sans-regular.woff2
│   ├── ibm-plex-sans-medium.woff2
│   └── ibm-plex-sans-semibold.woff2
└── images/
    ├── profile-hongyu-ding.webp
    └── papers/
        ├── uni-lavira.webp
        ├── lavira.webp
        └── mfrs.webp
```

If an official teaser cannot be obtained for a paper, omit that image file and add a text-only modifier to the corresponding publication article.

## 15. Responsive Rules

### Wide desktop: 1280–1920 px

- Center the 940 px content column.
- Use the full two-column hero and publication layouts.
- Research themes use three columns.

### Tablet: 768–1279 px

- Preserve two-column hero and paper rows where content remains comfortable.
- Reduce gaps and portrait width, not body-text size.

### Mobile: 375–767 px

- Stack hero content and portrait.
- Stack publication media above text.
- Stack research themes.
- Stack News dates above their text when needed.
- Keep all resource links wrap-capable and at least approximately 44 px high when presented as discrete controls.

At every target width:

- No horizontal overflow
- No clipped author lines or titles
- No off-screen portrait
- No fixed-width iframe or media

## 16. Accessibility and Interaction

- Use one `h1` for the name and sequential `h2`/`h3` headings.
- Add a skip link targeting the main content.
- Use visible `:focus-visible` outlines.
- Underline text links or provide an equally visible non-color cue.
- Keep primary text contrast at WCAG AA or better.
- Use meaningful image alt text.
- Mark decorative media with empty alt text only when adjacent text fully describes it.
- Do not open links in new tabs by default.
- Do not require pointer hover to reveal information.
- Respect `prefers-reduced-motion`; the first release should use no meaningful motion.
- Provide print CSS that removes nonessential decoration and keeps URLs or link meaning understandable.

## 17. Performance and Failure Behavior

- Use optimized WebP images with explicit width and height.
- Load the hero portrait eagerly and selected-paper images lazily.
- Self-host fonts and use `font-display: swap`.
- Keep the page functional with fonts unavailable.
- Keep the page functional with JavaScript disabled.
- Hide unavailable resource labels rather than rendering empty or disabled links.
- If a teaser fails, retain the complete text publication entry.
- Do not add analytics, cookies, trackers, or third-party scripts in the first release.

## 18. Verification Plan

1. Serve the directory over a local HTTP server.
2. Open the page in headless Chromium with Playwright.
3. Capture full-page screenshots at 375, 768, 1280, and 1920 px widths.
4. Assert that `document.documentElement.scrollWidth` does not exceed the viewport width.
5. Confirm all expected headings, five News entries, three selected publications, three compact publication citations, and the Academic Service state are present.
6. Confirm Email, Scholar, GitHub, Paper, Project, Code, and Video targets match the verified URLs in this specification.
7. Confirm all local images and font files load without console or network errors.
8. Test keyboard traversal and visible focus states.
9. Test the reduced-motion media query.
10. Inspect the page with fonts disabled or blocked to verify fallback readability.
11. Run an HTML validation pass and inspect CSS for syntax errors.
12. Run the mandatory code-review agent after implementation.
13. Perform a final visual review at all four target widths and fix only observed problems.

## 19. Acceptance Criteria

The design is implemented when:

- The page matches the approved Evidence-Led Editorial direction.
- All public identity and publication facts match this specification.
- The supplied portrait is used through the approved rectangular crop.
- The first release contains no CV link.
- Exactly five News entries appear.
- Exactly three Research themes appear.
- Exactly three selected publications appear with accurate links.
- The compact Publications section lists the complete current three-paper set.
- Academic Service displays `Details coming soon.`
- All four target viewport tests pass without horizontal overflow.
- Keyboard focus, heading hierarchy, alt text, and font fallbacks are verified.
- No generated research imagery, analytics, dark theme, or out-of-scope section is introduced.
