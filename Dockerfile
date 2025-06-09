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

# Copy the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose the application port
EXPOSE 10000

# Start the app with entrypoint that fetches the artifact at runtime
ENTRYPOINT ["/app/entrypoint.sh"]