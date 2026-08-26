#!/usr/bin/env bash
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
BUILD="$REPO/encyclopedia/out"
DEPLOY="/tmp/fish-deploy-$$"

echo "Building..."
uv run python3 "$REPO/encyclopedia/generate.py"

echo "Deploying to gh-pages..."
rm -rf "$DEPLOY"
git clone --branch gh-pages "git@github.com:sbOogway/fish.git" "$DEPLOY" 2>/dev/null || \
  git clone --orphan gh-pages "git@github.com:sbOogway/fish.git" "$DEPLOY"
cd "$DEPLOY"
git rm -rf . 2>/dev/null || true
cp -r "$BUILD"/* .
touch .nojekyll
git add -A
if git diff --cached --quiet; then
  echo "No changes to deploy."
else
  git commit -m "Deploy $(date +%Y-%m-%d)"
  git push origin gh-pages
  echo "Deployed! https://sboogway.github.io/fish/"
fi
rm -rf "$DEPLOY"
