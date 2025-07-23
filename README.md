# Database Schema Specification

🏢 **Standardized, modular JSON Schema specification** for database structure definition and validation. Designed for scalability, maintainability, and seamless integration with AI systems.

## 🏗️ Architecture

Our modular architecture prevents code duplication and enables effortless database version management:

```
specs.json                                    # 🎯 Main orchestrator with $schema/$id
schemas/
├── base/
│   ├── database.json                        # Database engine definitions
│   └── schema.json                          # Core schema structure
└── engines/
    └── postgresql/
        └── v15.0/                           # Version-specific isolation
            ├── schema.json                  # PostgreSQL 15.0 rules
            └── components/                  # Version-specific components
                ├── table.json               # Table definitions for v15.0
                ├── column.json              # Column types for v15.0
                └── constraint.json          # Constraints for v15.0
```

## FSD

- **FSD**: [Full Specification Document](https://www.notion.so/Database-Engines-Support-237bed96279c80ee85c1e69cf2abc42f) - Comprehensive guide to the database schema specification.
