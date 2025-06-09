#!/bin/bash
set -e

echo "📦 Starting container..."

# Validate env
echo "🔒 GITHUB_TOKEN: ${GITHUB_TOKEN:0:4}****"
echo "📦 Repo: $GITHUB_REPO_OWNER/$GITHUB_REPO_NAME"

echo "⬇️ Downloading gun-database artifact..."
ARTIFACT_JSON=$(curl -s -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  "https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/actions/artifacts")

echo "📄 Artifact JSON retrieved"

ARTIFACT_URL=$(echo "$ARTIFACT_JSON" | jq -r '.artifacts[] | select(.name=="gun-database") | .archive_download_url')

if [ -z "$ARTIFACT_URL" ]; then
  echo "❌ No gun-database artifact found."
  exit 1
fi

echo "🔗 Artifact URL: $ARTIFACT_URL"

curl -sL -H "Authorization: token ${GITHUB_TOKEN}" \
  -H "Accept: application/vnd.github.v3+json" \
  "$ARTIFACT_URL" -o gun-database.zip

echo "📂 Unzipping artifact..."
unzip -o gun-database.zip
mv artifacts/all_guns_database.json . || { echo "❌ JSON move failed"; exit 1; }

echo "🧹 Cleaning up..."
rm -rf artifacts gun-database.zip

echo "🚀 Starting bot..."
python start.py