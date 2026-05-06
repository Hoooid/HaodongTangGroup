# Nanophotonics Website Maintenance

This repository is the source for https://nanophotonics.cc/.

## Ownership and Access

- GitHub repository: `Hoooid/HaodongTangGroup`
- Hosting: GitHub Pages, deployed by `.github/workflows/publish.yaml`
- Domain: `nanophotonics.cc`
- Recommended permission model: Professor Tang remains repository owner, and the maintainer account is added as an `Admin` collaborator.
- Daily maintenance should be performed from the maintainer's own GitHub account, not by repeatedly logging in as Professor Tang.
- Any local screenshot containing Professor Tang's authorized account credentials is treated as an authorization record. Keep it outside this repository and never commit it.

Security checklist:

1. Use the maintainer's own GitHub collaborator account for commits, pushes, and pull requests.
2. Do not commit screenshots, passwords, tokens, or other account credentials to this repository.
3. Keep Professor Tang's GitHub password as an emergency fallback only if explicitly authorized.
4. After maintainer access is confirmed, recommend changing any exposed password and enabling GitHub two-factor authentication.
5. If `gh auth status` reports an invalid token, re-authenticate the maintainer account with `gh auth login -h github.com`.

## Local Setup

Use Hugo `0.119.0` to match the GitHub Actions workflow.

```sh
git clone https://github.com/Hoooid/HaodongTangGroup.git
cd HaodongTangGroup
hugo version
hugo --minify --baseURL https://nanophotonics.cc/
```

If the system Hugo is newer and fails with Hugo Blox template errors, install or run Hugo `0.119.0` explicitly.

## Common Content Updates

### Add a News Post

Add a new post under:

```text
content/en/post/<YY-MM-DD-short-title>/index.md
```

Use an existing post as the template. Put the cover image in the same folder as `featured.*` when the post needs a thumbnail.

### Add Publications

Update:

```text
publications.bib
```

Pushing changes to `publications.bib` triggers `.github/workflows/import-publications.yml`, which opens a pull request that imports the BibTeX entries into `content/publication/`.

Review the generated PR before merging.

### Chinese Content

The Hugo language configuration includes `zh` with `contentDir: content/zh`, and the site header language switch is enabled.

When adding Chinese pages, keep them in the same repository under `content/zh` instead of creating a separate Chinese repository. Mirror the English structure first, then translate high-value pages such as the homepage, people, posts, publications, and contact pages.

Current Chinese content structure:

```text
content/zh/_index.md
content/zh/vision/
content/zh/people/
content/zh/post/
content/zh/publication/
content/zh/contact/
content/zh/authors/
```

Publication pages are mirrored so the Chinese publications list is populated. Keep paper titles and citation metadata faithful to the original publication records unless Professor Tang provides official Chinese titles.

### New Paper Announcement Routine

For every newly accepted or published paper:

1. Add or update the BibTeX entry in `publications.bib`.
2. Write a news post under `content/en/post/<YY-MM-DD-short-title>/index.md`.
3. Write the matching Chinese post under `content/zh/post/<YY-MM-DD-short-title>/index.md`.
4. Include the paper title, authors, journal/conference, DOI or URL, short research background, key contribution, and an image if available.
5. If the publication import workflow opens a generated PR, review the generated publication pages before merging.

Use `CONTENT_WRITING_GUIDE.md` for the repeatable paper-post structure. In short: verify the bibliographic facts first, extract or download authorized original paper figures from the PDF or publisher page, create a raster `featured.*` thumbnail from one of those figures, write the lead and `<!--more-->` excerpt, explain the background and challenge, then walk readers through the original figures with short figure-led explanations. For review or perspective articles, emphasize the field map and evaluation framework rather than treating the article like an original experimental result. Do not publish important paper highlights as text-only posts, and do not redraw paper-style figures when the intended source is the paper PDF itself; redraw only when original figures cannot be reused or the user explicitly asks for new diagrams.

Google Scholar can be used as a discovery checklist, but it should not be treated as an automatic source of truth because it has no stable official sync API for this static Hugo site. For routine maintenance, open Professor Tang's Google Scholar profile, check the three newest records, then add confirmed papers to `publications.bib` and write news posts in the style of a WeChat public-account article.

### Performance Notes

Keep the production site lightweight for visitors in mainland China:

1. Avoid adding third-party scripts unless they are necessary.
2. Compress large photos before committing them; target a practical web size rather than uploading original phone/camera files.
3. Prefer local site assets over CDN-hosted dependencies.
4. Test major pages without relying on a proxy or VPN when possible.

## Deployment Checks

After merging changes to `main`:

1. Open GitHub Actions and confirm `Deploy website to GitHub Pages` succeeds.
2. Visit https://nanophotonics.cc/ and confirm the updated page is live.
3. Check that `https://www.nanophotonics.cc/` also resolves.
4. If the custom domain breaks, verify GitHub Pages settings and DNS before changing repository content.

Current DNS expectations:

- Apex domain `nanophotonics.cc`: GitHub Pages A records.
- `www.nanophotonics.cc`: CNAME to `hoooid.github.io`.

## Monthly Routine

- Publish one or two group news posts.
- Add newly accepted or published papers to `publications.bib`.
- Mirror important news posts in Chinese under `content/zh/post/`.
- Merge generated publication PRs after review.
- Check GitHub Actions for failed builds.
- Verify both English and Chinese homepage, posts, people, publications, and contact pages on production.
