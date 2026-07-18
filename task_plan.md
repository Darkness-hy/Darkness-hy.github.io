# Task Plan: Hongyu Ding Academic Homepage

## Goal
Design and implement a restrained, research-first academic homepage for Hongyu Ding, using the supplied portrait, verified publication information, and the structural strengths of the Finn/Xu/Barron reference sites.

## Phases
- [x] Phase 1: Explore the workspace, references, scholar profile, and personal taste document
- [x] Phase 2: Clarify only requirements that materially change the result
- [x] Phase 3: Compare 2–3 design approaches and obtain design approval
- [x] Phase 4: Write and review the approved design specification
- [x] Phase 5: Write the implementation plan and obtain execution approval
- [x] Phase 6: Implement the homepage and content model
- [x] Phase 7: Review code, test responsive behavior, and visually refine
- [x] Phase 8: Deliver the finished site with exact file and verification reporting

## Key Questions
1. Which identity/contact facts and links cannot be discovered reliably from the supplied sources?
2. Which selected-publication links and teaser assets are available now versus needing safe placeholders?
3. Should the first release be a static deployable site or use an existing framework found in the workspace?
4. What visual direction best communicates mature robotics research without looking generic or over-designed?

## Decisions Made
- Use the user-supplied portrait at `figs/ChatGPT Image 2026年6月29日 16_41_32.png`.
- Keep the homepage focused on biography, research direction, five recent news items, selected publications, complete publications, and academic service.
- Exclude standalone Awards, Teaching, Mentorship, media carousel, lab-member pages, citation counters, and a complex dark theme from the first release.
- Treat Danfei Xu / Jon Barron as the structural base, with project-first summaries and visual publication cards.
- This directory is not a Git repository; design/spec commits are not possible unless the user later initializes Git.
- Public identity line: `PhD Student at Nanjing University`.
- Public email link: `mailto:hongyuding@smail.nju.edu.cn`.
- CV link: omit from the first release rather than showing a placeholder.
- Personal GitHub link: `https://github.com/Darkness-hy`.
- Hero research thesis: `I study embodied intelligence, focusing on how language, vision, and robot actions can be translated into unified navigation and decision-making systems.`
- First-release assumption: the verified three papers are both the selected and complete publication set until more records are supplied.
- First-release assumption: derive five concise News items only from verified public milestones; do not invent announcements.
- Academic Service may use a restrained `Details coming soon.` state until entries are supplied.
- A static semantic site is the recommended implementation because the workspace has no existing framework and the page needs no application state.
- Approved visual direction: `Evidence-Led Editorial`.
- Approved structural system: 940 px semantic single page; warm paper/ink/brick palette; Newsreader + IBM Plex Sans; 2:1 hero with 4:5 portrait; no large navigation; mobile stack below about 700 px.
- Approved content system: five verified News items; three research themes; three expanded selected-publication entries; compact year-grouped full Publications; Academic Service coming-soon state.
- Written design specification: `plan/2026-07-14-academic-homepage-design.md` (463 lines, 2,391 words).
- Specification self-review found no placeholder markers or internal scope contradictions.
- Written implementation plan: `plan/2026-07-14-academic-homepage-implementation.md` (1,640 lines, 5,002 words before final URL corrections).
- Implementation-plan self-review verified the required header, four task boundaries, checkbox tracking, four target viewports, package-version availability, and all four font source URLs.
- User approved Subagent-Driven execution and explicitly authorized initializing a local Git repository; no remote repository or push is authorized.

## Errors Encountered
- Implementation-plan review workflow failed on 2026-07-14 because all five agents received temporary API 500/EOF connection errors. Resolution: retried once; the retry remained stuck without results and was stopped after the implementation plan had been completed and self-reviewed inline.
- Local tool check: `uv` and ImageMagick are unavailable; `/usr/bin/python3`, `npx`, `/usr/bin/sips`, and `/usr/bin/tidy` are available. The implementation plan must not assume `uv` or `magick`.
- Task 4 delegation was initially denied because `npx --yes html-validate` may download and execute an unapproved external npm package. Resolution: completed all local checks first, then obtained explicit approval for `html-validate` from the official npm registry; version 11.4.0 found one doctype-style error, which was fixed and revalidated with zero errors.
- Final whole-branch review confirmed five defects: missing printed link destinations, converted IBM Plex files with reserved-family-name risk, unenforced static runtime/content contracts, incomplete exact-record tests, and generated mode `0600`. Resolution: fixed and committed in `18647d4`.
- Follow-up code review found that the Newsreader conversion test used synthetic descriptors and did not protect the production conversion route. Resolution: added a pinned real-source fixture and mutation-proven regression in `ab42725`.
- Follow-up visual review found A4 section headings could be orphaned from their first content item. Resolution: added print-only break avoidance and a Chromium regression in `eadfc83`; independent code and visual re-reviews approved the result.
- Apple Tidy build 4474 reports valid HTML5 elements as unsupported. Resolution: the documented UTF-8/custom-tag compatibility command exits `1` with zero structural diagnostics; `html-validate 11.4.0` exits `0`.

## Status
**Complete** — implementation, responsive and print verification, licensing/provenance checks, exact content contracts, final code review, and final visual review all passed. Local delivery state is recorded; no remote, push, deployment, or publication action was performed.
