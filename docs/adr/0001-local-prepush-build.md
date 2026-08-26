# Local pre-push build over CI/CD

We build the encyclopedia site locally via a pre-push git hook (pre-commit framework) instead of GitHub Actions. Validation + HTML generation run before every push. Build output (`encyclopedia/out/`) is gitignored.

GitHub Actions was considered but rejected: this is a single-developer project with 196 static pages that build in under a second. CI adds deployment complexity (workflow files, GitHub Pages config, secrets) with no benefit. A pre-push hook is simpler, faster, and keeps the build close to the source. If CI is needed later, it's one workflow file away.
