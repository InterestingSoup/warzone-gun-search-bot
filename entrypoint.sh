#!/bin/bash
set -e

echo "📦 Starting container..."
echo "⬇️ Downloading gun-database artifact..."

ARTIFACT_JSON=$(curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/actions/artifacts")

ARTIFACT_URL=$(echo "$ARTIFACT_JSON" | jq -r '.artifacts[] | select(.name=="gun-database") | .archive_download_url')

if [ -z "$ARTIFACT_URL" ]; then
  echo "❌ No artifact found."
  exit 1
fi

curl -sL -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/zip" "$ARTIFACT_URL" -o gun-database.zip

unzip -o gun-database.zip
mv artifacts/all_guns_database.json .
rm -rf gun-database.zip artifacts

echo "✅ Artifact downloaded. Starting app..."
exec python start.py