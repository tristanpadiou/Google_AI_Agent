# Use Python 3.13.2 as the base image
FROM python:3.13.2-slim

# Install system dependencies as root first
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create user after system packages are installed
RUN useradd -m -u 1000 user
USER user

# Set home to the user's home directory
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

# Set the working directory
WORKDIR $HOME/app

# Create directories with proper permissions for app data
RUN mkdir -p $HOME/app/logs $HOME/app/data $HOME/app/tmp && \
    chmod -R 755 $HOME/app

# Copy requirements first to leverage Docker cache
COPY --chown=user:user requirements.txt .

# Install Python dependencies with more specific options
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --timeout=1000 -r requirements.txt

# Copy the application code
COPY --chown=user:user . $HOME/app

# Ensure all app files have proper permissions
RUN chmod -R 755 $HOME/app && \
    find $HOME/app -type f -name "*.py" -exec chmod 644 {} \;

# Expose the port the app runs on
EXPOSE 7860

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7860/health || exit 1

# Run the application with uvicorn
CMD ["uvicorn", "google_agent_api:app", "--host", "0.0.0.0", "--port", "7860"] 