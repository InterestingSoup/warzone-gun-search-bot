FROM python:3.11-slim

# Define build arguments
ARG GITHUB_TOKEN
ARG GITHUB_REPO_OWNER
ARG GITHUB_REPO_NAME

# Install system dependencies
RUN apt-get update && apt-get install -y \
    jq \
    curl \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better caching
COPY discord_bot_requirements.txt .
RUN pip install --no-cache-dir -r discord_bot_requirements.txt

# Copy rest of the application
COPY . .

RUN echo "Using GitHub token: ${GITHUB_TOKEN}" && [ ! -z "$GITHUB_TOKEN" ] || (echo "❌ GITHUB_TOKEN is missing!" && exit 1)

# Download latest gun database artifact
RUN set -e && \
    echo "📦 Starting artifact fetch..." && \
    echo "👀 Getting artifact list from GitHub..." && \
    ARTIFACT_JSON=$(curl -v -s -H "Authorization: token ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github.v3+json" \
      "https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/actions/artifacts") && \
    echo "📄 Artifact JSON: $ARTIFACT_JSON" && \
    ARTIFACT_URL=$(echo "$ARTIFACT_JSON" | jq -r '.artifacts[] | select(.name=="gun-database") | .archive_download_url') && \
    echo "🔗 Artifact URL: $ARTIFACT_URL" && \
    if [ -z "$ARTIFACT_URL" ]; then \
        echo "❌ Error: Could not find gun-database artifact." && exit 1; \
    fi && \
    echo "⬇️ Downloading artifact..." && \
    curl -v -sL -H "Authorization: token ${GITHUB_TOKEN}" \
      -H "Accept: application/vnd.github.v3+json" "$ARTIFACT_URL" -o gun-database.zip && \
    echo "📂 Unzipping artifact..." && \
    unzip -l gun-database.zip && \
    unzip -o gun-database.zip && \
    echo "📁 Moving JSON file..." && \
    mv artifacts/all_guns_database.json . && \
    echo "🧹 Cleaning up..." && \
    rm -rf artifacts gun-database.zip && \
    echo "✅ Artifact setup complete"


# Expose port
EXPOSE 10000

# Start app
CMD ["python", "start.py"]