# Database Schema Spec Generator

A Python package for generating unified JSON documentation files for database schemas by resolving JSON Schema references and handling oneOf variants. This tool processes modular database schema specifications and generates consolidated documentation for different database engines and versions.

## 🚀 Quick Start

### Prerequisites

- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. Clone the repository:

```bash
git clone <repository-url>
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
│   ├── specs.json                  # Main schema file
│   └── schemas/                    # Schema definitions
└── output/                         # Generated output files
    ├── vmap.json                   # Version mapping
    └── postgresql/                 # Database-specific outputs
```

## 🧪 Development

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
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

# Run pre-commit on all files
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

- **Input Directory**: `docs/` (contains source schema files)
- **Output Directory**: `output/` (generated files are written here)
- **Root Schema File**: `docs/specs.json`

## 📤 Output

The generator creates:

- **Unified Schema Files**: Consolidated schemas for each database variant
- **Version Map** (`vmap.json`): Mapping of available database versions
- **Database-Specific Directories**: Organized by engine and version

Example output structure:

```
output/
├── vmap.json
└── postgresql/
    └── 15.0/
        └── unified_schema.json
```
