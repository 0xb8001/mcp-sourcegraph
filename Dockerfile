FROM python:3.11.9-slim

# Set working directory
WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml README.md .

# Upgrade pip and install build dependencies first
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Install the package in editable mode
RUN pip install --no-cache-dir -e .

# Copy application code
COPY mcp_sourcegraph/ ./mcp_sourcegraph/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Expose port (MCP servers typically use stdio, but having port available)
EXPOSE 8000

# Default command to run the MCP server
CMD ["python", "-m", "mcp_sourcegraph.server"]