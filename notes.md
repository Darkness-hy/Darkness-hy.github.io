# Notes: Hongyu Ding Academic Homepage

## Local Inputs

### Personal portrait
- Required source: `figs/ChatGPT Image 2026年6月29日 16_41_32.png`.
- Format: portrait photograph, 1118 × 1408 px.
- Visual characteristics: centered upper-body portrait; bright white clothing; traditional architecture and warm red accents in the background.
- Design implication: use a calm 4:5 rectangular crop with a subtle corner radius; avoid circular cropping because the environmental context gives the portrait character.
- Nearby alternatives under `figs/11/` use stronger background blur and square crops, but the user explicitly selected the required source. They remain untouched and should not silently replace it.

### Insight and taste document
- Path: `hongyu-insight-taste.md`
- Relevant principles:
  - Prefer mature, restrained, product-grade visuals.
  - Avoid generic technology styling, cheap gradients, meaningless glow, and decorative clutter.
  - Lead with a clear claim, then evidence and a concrete path.
  - Favor simple-yet-effective structure, strong alignment, useful whitespace, and exact typography.
  - Public-facing copy should have a point of view without reading like advertising.

## User-Specified Scope
- Header/profile: portrait, name, one-line identity, research interests, Email/CV/Scholar/GitHub.
- Main sections: News, Research, Selected Publications, Publications, Academic Service.
- News: latest five items only.
- Selected publications: three to five visual cards with one-sentence summaries and resource links.
- Do not add standalone Awards, Teaching, Mentorship, citation counters, media carousel, lab-member pages, or a complex dark theme.

## Selected Publications Supplied by User
1. Uni-LaViRA: Language-Vision-Robot Actions Translation for Unified Embodied Navigation.
2. LaViRA: Language-Vision-Robot Actions Translation for Zero-Shot Vision Language Navigation in Continuous Environments.
3. Magnetic field-based reward shaping for goal-conditioned reinforcement learning.

## Reference Sources
- Chelsea Finn: https://ai.stanford.edu/~cbfinn/
- Danfei Xu: https://faculty.cc.gatech.edu/~danfei/
- Jon Barron: https://jonbarron.info/
- Google Scholar: https://scholar.google.com/citations?user=IvWH8tcAAAAJ&hl=zh-CN&authuser=1&oi=ao

## Design-System Retrieval Notes
- The helper matched an editorial portfolio structure: hero → selected work → evidence, with typography carrying most of the distinction.
- Useful guidance: semantic HTML, consistent spacing/type scales, visible focus rings, and restrained motion.
- Rejected literal defaults: charcoal-lime palette and Space Grotesk/Inter would feel too startup-like and generic for this brief.
- Better direction to evaluate: warm paper background, ink/charcoal text, one muted vermilion accent sampled conceptually from the portrait, and a research-editorial serif/sans pairing.

## Verified Reference Findings
- Finn, Xu, and Barron consistently validate a compact identity-first hero, direct high-value links, a centered 800–900 px reading width, and restrained color.
- Danfei Xu’s strongest transferable pattern is the publication schema: teaser → title → authors → venue/status → literal resource links → short capability summary.
- The legacy templates must not be copied literally: they use fixed/table layouts, weak semantics, missing mobile reflow, hover-only media, and—in Finn/Xu—measured horizontal overflow at 375 px.
- Recommended implementation adaptation: semantic HTML, CSS Grid/Flexbox, responsive stacking, one structured publication dataset, visible keyboard focus, reduced-motion behavior, and no autoplay media.

## Verified Profile and Publication Facts
- Google Scholar profile name: Hongyu Ding.
- Affiliation shown by Scholar: Nanjing University.
- Scholar interests: Embodied AI, Robotics, Reinforcement Learning.
- Uni-LaViRA: arXiv preprint, 2026; verified Paper, Project, and Code URLs; no direct public video or author-released dataset verified.
- LaViRA: preprint first posted in 2025; ICRA 2026 acceptance is stated by author-controlled project/arXiv sources, while the checked tentative official author index did not yield an exact match; verified Paper, Project, and Code URLs.
- Magnetic Field-Based Reward Shaping: IEEE/CAA Journal of Automatica Sinica 10(12):2233–2247, 2023; verified Paper/DOI, Project, Code, and Video URLs.
- The Scholar profile exposes only the verified email domain `smail.nju.edu.cn`, not the full address.

## Recommended Direction From Research
- Preferred: **Evidence-Led Editorial** — warm paper background, dark ink text, muted brick-red accent, compact identity hero, five News items, research themes, visual selected-publication rows, dense year-grouped complete bibliography, and compact Academic Service.
- Fallback: **Modernized Academic Index** — closest to Danfei Xu/Jon Barron, lower maintenance, but more derivative.
- Minimal option: **Text-First Scholarly Ledger** — fastest and most accessible, but underuses embodied-navigation media.

## Confirmed by User
- Public role: PhD Student at Nanjing University.
- Public email: `hongyuding@smail.nju.edu.cn`.
- CV: omit from the first release; do not show a disabled or coming-soon CV link.
- Personal GitHub: `https://github.com/Darkness-hy`.
- Research thesis: “I study embodied intelligence, focusing on how language, vision, and robot actions can be translated into unified navigation and decision-making systems.”
- Research themes inferred and accepted by this choice: Language–Vision–Action Translation; Embodied Navigation; Reinforcement Learning.

## Approved Visual Direction
- Evidence-Led Editorial.
- Warm paper background, dark ink typography, muted brick-red accent, compact two-column hero, real research media, and no decorative technology motifs.
- Approved visual system: `Newsreader` for name/section display, `IBM Plex Sans` for body/metadata; 940 px main container; 2:1 desktop hero; no large navigation; 4:5 rectangular portrait; single-column mobile reflow below about 700 px.

## Approved Content Components
- Five News items derived only from verified milestones: Uni-LaViRA release; LaViRA ICRA 2026 update; LaViRA initial release; MFRS journal publication; MFRS project/code/video release.
- Research themes: Language–Vision–Action Translation; Unified Embodied Navigation; Goal-Conditioned Reinforcement Learning.
- Three selected-paper summaries approved; show only verified resource labels.
- Complete Publications repeats the same current three records in compact year-grouped form.
- Academic Service uses `Details coming soon.` until user-supplied entries exist.

## First-Release Assumptions After “Continue”
- Treat the verified three papers as the current complete publication set; Selected Publications uses expanded visual rows and Publications uses compact citations from the same data.
- Create five News lines only from verified publication/project milestones; every line remains editable content.
- Use `Details coming soon.` for Academic Service rather than inventing roles.
- Omit CV entirely.
- Prefer a dependency-free static site because no existing application stack is present.

## Open Facts to Verify
- Preferred department/lab wording, if any, for the identity or biography.
- Public email, CV URL/file, GitHub URL, and any project/code/video/dataset links.
- Exact author lists, venues, years, and publication status for selected papers.
- Five news entries and Academic Service details.
