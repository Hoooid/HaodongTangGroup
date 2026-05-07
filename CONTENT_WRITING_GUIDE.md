# Paper News Writing Guide

This guide records the repeatable structure for turning a new paper, review, comment, or conference output into a figure-rich website post for `nanophotonics.cc`.

For tone-specific rules, especially Chinese "academic celebration" posts and metric-to-imaging translation, also use `PAPER_POST_EDITORIAL_GUIDE.md`.

## Goal

Each post should help a non-specialist reader understand:

1. What was published.
2. Why the topic matters.
3. What problem the work addresses.
4. What the main contribution or organizing framework is.
5. Why the result matters for devices, systems, applications, or the field.

Avoid copying the abstract. Convert the paper into a clear public-facing story with figures, captions, and short explanatory paragraphs.

## Source Intake

Before writing, collect and verify:

- Paper title, journal or conference, publication date, DOI or stable URL.
- Author list and corresponding lab members.
- Paper type: original research, review, comment, perspective, cover article, conference news, award, or group activity.
- Core topic and target audience.
- Three to five concrete technical anchors, such as material system, device structure, method, benchmark metric, figure logic, or application scenario.
- Paper PDF or publisher page with figure assets.
- Whether original paper figures are authorized for reuse. If they are available and authorized, use the original figures first; redraw simplified explainer figures only when figures cannot be reused, cannot be extracted cleanly, or the user explicitly asks for new diagrams.

## Visual Standard

Every important paper post should be figure-led, not text-only.

Minimum visual package:

1. `featured.*`: a raster thumbnail derived from the paper's first figure, cover image, or another authorized paper visual.
2. `figure-1.*`, `figure-2.*`, etc.: original paper figures extracted from the PDF or downloaded from the publisher when authorized.
3. Optional local redraws only when they clarify a point that the original figures do not show.

For review articles, use original figures as the backbone of the post:

- Use the review's material map, device diagrams, metric panels, strategy summaries, and system-integration figures directly when available.
- Write one short lead-in before each figure and one plain-language explanation after each figure.
- Translate figure content into the website story instead of replacing the paper's figures with newly drawn graphics.

For original research articles, use the paper's actual figures to explain the contribution:

- Problem schematic: what was limiting performance before.
- Method or mechanism schematic: what the authors changed.
- Result summary: the key performance numbers and why they matter.
- Figure-style reading: what Figures 1, 2, 3, etc. each prove.

Do not publish a paper highlight without images unless no visual source or redraw can be made. Do not redraw paper-like figures when the user expects the original PDF figures.

## Directory Pattern

Create mirrored posts when the content is important for both language versions:

```text
content/en/post/<YY-MM-DD-short-slug>/index.md
content/zh/post/<YY-MM-DD-short-slug>/index.md
```

Use the same slug in both languages. Keep front matter minimal unless the local Hugo theme requires more:

```yaml
---
title: Paper Highlight | Short Descriptive Title
date: YYYY-MM-DD
---
```

Place `<!--more-->` after the opening summary paragraph so the list page has a clean excerpt.

## Standard Structure For Original Research

Use this order for most newly published research papers:

1. Opening summary: publication venue, paper title, and one-sentence contribution.
2. Cover image or first explainer figure.
3. Paper Information: title, journal, date, DOI, authors.
4. Background: why the scientific or technical problem matters.
5. Challenge: what blocked previous materials, devices, measurements, or systems.
6. Mechanism or method figure: what the authors changed.
7. What This Work Did: method, material design, device design, or workflow.
8. Results figure: concrete metrics and observations, with measurement conditions when available.
9. Figure-Style Reading: explain the paper's figure sequence as a story.
10. Takeaway: one paragraph connecting the result to future work or applications.
11. Congratulations line when appropriate.

## Standard Structure For Reviews And Perspectives

Use this order when the paper is a review, comment, or perspective:

1. Opening summary: publication venue and the review's central map.
2. Cover image or review roadmap figure.
3. Paper Information.
4. Why This Topic Matters.
5. Main Structure Of The Review: the review's conceptual framework, supported by a roadmap figure.
6. How To Read The Metrics Or Concepts: define the evaluation logic, supported by a metric-decoder figure.
7. Key Improvement Routes Or Field Directions, supported by a strategy figure.
8. From Devices To Systems, Applications, Or Standards, supported by a system figure.
9. Takeaway: summarize the framework in one strong sentence or paragraph.

## Writing Method

Write from the reader's question sequence:

- What is this about?
- Why should I care?
- What was hard before?
- What did the authors clarify or achieve?
- What evidence or metrics support it?
- What changes after this work?

For technical content, translate jargon into causal links and place at least one causal link next to each figure:

- Material change -> surface or structure effect -> carrier transport or recombination effect -> device metric -> imaging or system impact.
- Measurement protocol -> uncertainty or comparability -> benchmark reliability -> field-level consequence.
- Device architecture -> dark current, noise, response speed, linearity, or integration impact.

## WeChat-Style Article Pattern

For posts intended to feel like a public-account article:

1. Start with a short context paragraph, then a cover image.
2. Use one-sentence section openers.
3. Keep paragraphs short. One paragraph should usually carry one idea.
4. Use bold or restrained red inline emphasis for the core sentence, not for decoration.
5. Put a figure before or immediately after the paragraph that introduces the concept.
6. After each figure, write a plain-language caption paragraph: what the reader should see and why it matters.
7. End with paper information, DOI, and a concise takeaway if the post is intended for broad sharing.

## Style Rules

- Keep the post accurate, concise, and readable.
- Use original paper titles and DOI exactly.
- Spell out abbreviations at first use.
- Keep claims tied to the paper. Do not add unsupported commercial claims.
- Use metrics only with their units and measurement wavelength or bias when available.
- Prefer short paragraphs and section headings.
- Use figures as part of the argument, not as decoration.
- If using red emphasis, keep it sparse and reserved for the core takeaway sentence.
- Avoid overusing emojis in research posts; existing older posts may contain them, but the cleaner format is preferred for new technical highlights.
- For Chinese posts, use Chinese scientific names where natural, while keeping original English paper titles in the Paper Information section.
- For English posts, translate the story, not sentence by sentence from the Chinese version.

## Final Checklist

Before publishing:

- Both `content/en/post/...` and `content/zh/post/...` exist when bilingual publication is needed.
- The slug date and front matter date are intentional.
- `<!--more-->` is present after the lead paragraph.
- DOI/URL opens to the paper.
- Author names and affiliations are not accidentally mistranscribed.
- The post includes a cover or featured image plus at least two explainer figures.
- Any image references point to files in the same post directory or to stable local site assets.
- Each figure has a nearby explanatory paragraph.
- The local Hugo build succeeds.
