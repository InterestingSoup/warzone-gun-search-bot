#!/bin/bash
set -euo pipefail

echo "📦 Starting container..."
echo "🔒 GITHUB_TOKEN: ${GITHUB_TOKEN:0:4}****"
echo "📦 Repo: ${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}"

# Get artifact URL
echo "⬇️ Downloading gun-database artifact..."
ARTIFACT_JSON=$(curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/actions/artifacts")

echo "📄 Artifact JSON retrieved"

ARTIFACT_URL=$(echo "$ARTIFACT_JSON" | jq -r '.artifacts[] | select(.name=="gun-database") | .archive_download_url' | head -n 1)

if [ -z "$ARTIFACT_URL" ]; then
  echo "❌ Error: No artifact URL found."
  exit 1
fi

echo "🔗 Artifact URL: $ARTIFACT_URL"

# Download the artifact
echo "⬇️ Downloading artifact ZIP..."
curl -sSL -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "$ARTIFACT_URL" -o gun-database.zip || {
    echo "❌ Artifact download failed"
    exit 1
}

# Unzip and move the JSON file
echo "📂 Unzipping artifact..."
unzip -o gun-database.zip

if [ -f all_guns_database.json ]; then
  echo "✅ all_guns_database.json found at root, skipping move."
else
  echo "🔍 Searching for all_guns_database.json to move..."
  FILE_FOUND=$(find . -name "all_guns_database.json" -print -quit)

  if [ -n "$FILE_FOUND" ]; then
    mv "$FILE_FOUND" .
    echo "✅ Moved $FILE_FOUND to current directory."
  else
    echo "❌ Missing expected file in artifact."
    exit 1
  fi
fi

# Cleanup
rm -rf artifacts gun-database.zip

echo "🚀 Launching app..."
exec python start.py