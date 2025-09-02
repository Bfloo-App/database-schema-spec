# Multi-stage build for database schema spec generator
# Stage 1: Build the schemas
FROM ghcr.io/astral-sh/uv:0.8.13-alpine3.22 AS builder

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Copy source code and input files
COPY main.py ./
COPY database_schema_spec/ ./database_schema_spec/
COPY docs/ ./docs/
COPY .env ./

# Generate the schemas
RUN uv run python main.py

# Stage 2: Final lightweight image with only the output
FROM alpine:3.22 AS final

# Create output directory
RUN mkdir -p /output

# Copy generated schemas from builder stage
COPY --from=builder /app/output/ /output/

# Optional: Set a default command to list contents (for debugging)
CMD ["ls", "-la", "/output"]
