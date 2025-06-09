#!/bin/bash
set -e

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

echo "🔗 Artifact URL: $ARTIFACT_URL"

# Fail if URL is missing
if [ -z "$ARTIFACT_URL" ]; then
    echo "❌ Error: No artifact URL found."
    exit 1
fi

# Download the artifact
curl -L \
  -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github+json" \
  "$ARTIFACT_URL" -o gun-database.zip || {
    echo "❌ Artifact download failed"
    exit 1
}

# Unzip and move file
unzip -o gun-database.zip
mv artifacts/all_guns_database.json . || {
  echo "❌ Missing expected file in artifact."
  exit 1
}
rm -rf artifacts gun-database.zip

echo "✅ Artifact ready. Launching app..."

# Run your app
python start.py