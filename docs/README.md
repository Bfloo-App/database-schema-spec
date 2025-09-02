# Database Schema Specification

**Standardized, modular JSON Schema specification** for database structure definition and validation. Designed for scalability, maintainability, and seamless integration with AI systems.

## Architecture

Our modular architecture prevents code duplication and enables effortless database version management:

```
schemas/
├── _registry_.json                           # Engine/version registry
├── project/
│   ├── manifest.json                         # Snapshot manifest schema
│   └── config/
│       ├── base.json                         # Common project config schema
│       └── engines/
│           └── postgresql.json               # PostgreSQL connection config
└── engines/
    └── postgresql/
        └── v15.0/                            # Version-specific isolation
            ├── spec.json                     # Self-contained PostgreSQL 15.0 spec
            └── components/                   # Reusable schema components
                ├── table.json                # Table definitions
                ├── column.json               # Column types
                └── constraint.json           # Constraints
```

## Schema Types

### Project Schemas

| Schema | Purpose |
|--------|---------|
| `config/base.json` | Common config: schema_id, database.engine, api settings (including key) |
| `config/engines/postgresql.json` | PostgreSQL-specific connection parameters |
| `manifest.json` | Snapshot registry with version tracking |

### Engine Specs

Each engine/version combination has a self-contained `spec.json` that defines the complete schema for validating `schema.yaml` files.

## Environment Variable Resolution

The CLI supports environment variable references in configuration values using `${VAR_NAME}` syntax. This allows sensitive data like API keys and database passwords to be kept out of committed files.

### Syntax

```yaml
api:
  key: "${BFLOO_API_KEY}"

environments:
  production:
    password: "${PROD_DB_PASSWORD}"
```

### Resolution Order

The CLI resolves environment variables from:

1. **System environment** - Variables already set in the shell
2. **`.env` file** - Searched in these locations (first found wins):
   - Same directory as the config file
   - Project root (directory containing `.git`)
   - Current working directory

### CLI Override

```bash
# Specify a custom .env file location
db sync push --env-file /path/to/.env.production
```

### Security Notes

- Never commit `.env` files containing secrets (add to `.gitignore`)
- The `${VAR_NAME}` syntax is only resolved at CLI runtime
- Missing variables cause the CLI to fail with an error (no silent fallbacks)

## Generated Output

The generator produces resolved schemas with injected `$id` fields:

```
output/
├── smap.json                                 # Schema map (discovery file)
├── manifest.json                             # Manifest schema with $id
├── config/
│   ├── base.json                             # Base config with $id
│   └── engines/
│       └── postgresql.json                   # PostgreSQL config with $id
└── postgresql/
    └── v15.0/
        └── spec.json                         # Fully resolved spec with $id
```

### Schema Map (smap.json)

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

## FSD

- **FSD**: [Full Specification Document](https://www.notion.so/Database-Engines-Support-237bed96279c80ee85c1e69cf2abc42f) - Comprehensive guide to the database schema specification.
