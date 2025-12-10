# Database Schema Spec Generator

A Python package for generating unified JSON documentation files for database schemas by resolving JSON Schema references and handling oneOf variants. This tool processes modular database schema specifications and generates consolidated documentation for different database engines and versions.

## 🚀 Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. Clone the repository:

```bash
git clone https://github.com/Bfloo-App/database-schema-spec.git
cd database-schema-spec
```

2. Install dependencies using uv:

```bash
uv sync --frozen
```

3. Set up environment variables by creating a `.env` file:

```bash
cp .env.example .env
# Edit .env and set BASE_URL to your desired URL
```

**Note:** The `BASE_URL` environment variable is **required**. The application will fail to start if it's not set.

## 🏃‍♂️ Running the Application

### Using uv (Recommended)

```bash
# Run the schema generator
uv run main.py
```

### Using Python directly

```bash
# Activate the virtual environment first
source .venv/bin/activate  # On Unix/macOS
# or
.venv\Scripts\activate     # On Windows

# Then run
python main.py
```

## 📁 Project Structure

```
database-schema-spec/
├── main.py                           # Entry point
├── .env                             # Environment configuration
├── pyproject.toml                   # Project dependencies
├── database_schema_spec/            # Main package
│   ├── cli/                        # Command-line interface
│   ├── core/                       # Core functionality
│   │   ├── config.py               # Configuration management
│   │   ├── exceptions.py           # Custom exceptions
│   │   └── schemas.py              # Data models
│   ├── io/                         # Input/output handling
│   ├── logger/                     # Logging configuration
│   ├── resolution/                 # Schema resolution logic
│   └── validation/                 # Schema validation
├── docs/                           # Input schema files
│   └── schemas/
│       ├── _registry_.json         # Engine/version registry
│       ├── project/
│       │   ├── manifest.json       # Snapshot manifest schema
│       │   └── config/
│       │       ├── base.json       # Common config schema
│       │       └── engines/
│       │           └── postgresql.json  # PostgreSQL connection config
│       └── engines/
│           └── postgresql/
│               └── v15.0/          # Version-specific spec
│                   ├── spec.json
│                   └── components/
└── output/                         # Generated output files
    ├── smap.json                   # Schema map (discovery file)
    ├── manifest.json               # Manifest schema with $id
    ├── config/
    │   ├── base.json               # Base config with $id
    │   └── engines/
    │       └── postgresql.json     # PostgreSQL config with $id
    └── postgresql/
        └── v15.0/
            └── spec.json           # Fully resolved spec with $id
```

## 🧪 Development

### Running Tests

```bash
# Run all tests: NOTE some default flags are already set on puproject.toml
uv run pytest

# Run specific test file example
uv run pytest tests/test_integration.py

```

### Code Quality

```bash
# Lint code
uv run ruff check

# Format code
uv run ruff format

# Type checking
uv run pyright
```

### Pre-commit Hooks

```bash
# Install pre-commit hooks
uv run pre-commit install

# Run pre-commit *manually* on all files
# Once pre-commit is installed it should run everytime you attempt to commit changes on the changed files
uv run pre-commit run --all-files

```

## 📝 Environment Variables

| Variable   | Required | Description                         | Example                           |
| ---------- | -------- | ----------------------------------- | --------------------------------- |
| `BASE_URL` | ✅ Yes   | Base URL for generated schema files | `https://api.example.com/schemas` |

## 🔧 Configuration

The application can be configured through:

1. **Environment Variables**: Set in `.env` file or system environment
2. **Configuration Constants**: Defined in `database_schema_spec/core/config.py`

### Default Paths

- **Input Directory**: `docs/schemas/` (contains source schema files)
- **Output Directory**: `output/` (generated files are written here)
- **Registry File**: `docs/schemas/_registry_.json` (engine/version registry)

## 📤 Output

The generator creates:

- **Schema Map** (`smap.json`): Discovery file mapping all available schemas
- **Project Schemas**: Config and manifest schemas with injected `$id` fields
- **Engine Specs**: Fully resolved database-specific schemas organized by engine and version

Example output structure:

```
output/
├── smap.json                   # Schema map for discovery
├── manifest.json               # Manifest schema
├── config/
│   ├── base.json               # Base config schema
│   └── engines/
│       └── postgresql.json     # PostgreSQL config schema
└── postgresql/
    └── v15.0/
        └── spec.json           # PostgreSQL 15.0 spec
```

### Schema Map (smap.json)

The schema map provides a structured index of all generated schemas:

```json
{
  "project": {
    "manifest": "https://example.com/schemas/manifest.json",
    "config": {
      "base": "https://example.com/schemas/config/base.json",
      "engines": {
        "postgresql": "https://example.com/schemas/config/engines/postgresql.json"
      }
    }
  },
  "engines": {
    "postgresql": {
      "v15.0": "https://example.com/schemas/postgresql/v15.0/spec.json"
    }
  }
}
```
