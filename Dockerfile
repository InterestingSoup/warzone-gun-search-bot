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

# Copy application code
COPY . .

# Download latest gun database artifact
RUN curl -L -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github.v3+json" \
    "https://api.github.com/repos/${GITHUB_REPO_OWNER}/${GITHUB_REPO_NAME}/actions/artifacts" | \
    jq -r '.artifacts[] | select(.name=="gun-database") | .archive_download_url' | \
    xargs -I {} curl -L -H "Authorization: token ${GITHUB_TOKEN}" \
    -H "Accept: application/vnd.github.v3+json" {} -o gun-database.zip && \
    unzip gun-database.zip && \
    mv artifacts/all_guns_database.json . && \
    rm -rf artifacts gun-database.zip

# Expose port
EXPOSE 10000

# Start the application
CMD ["python", "start.py"] 