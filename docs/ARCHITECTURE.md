# Database Schema Specification - Architecture & File Structure

This document outlines the complete architecture for the database schema specification system, including file formats, CLI workflows, and API synchronization.

## Overview

The system supports two user personas:

1. **Visual Editor users** - Edit schemas in web application, sync to local files
2. **Code-first users** - Edit YAML files directly, sync to web application

Both workflows are supported through a clean separation of concerns: schema content vs. metadata.

---

## Project File Structure

```
/database/
├── config.yaml              # Project configuration (required)
├── schema.yaml              # Current working schema (clean, no metadata)
└── _history_/
    ├── manifest.yaml        # Snapshot registry with metadata
    ├── 2024-01-15_v1.0.0.yaml
    ├── 2024-03-20_v2.0.0.yaml
    └── 2024-05-15_v3.0.0.yaml
```

---

## File Specifications

### 1. `config.yaml` - Project Configuration

The configuration is split into two schemas that are combined:

1. **Base config** (`config/base.json`) - Common properties shared across all engines
2. **Engine config** (`config/engines/{engine}.json`) - Engine-specific connection parameters

This separation allows each database engine to have its own validated connection parameters while sharing common project settings.

#### Base Configuration

Contains project identification, database engine selection, and API settings.

```yaml
# Unique identifier linking this project to the web application
# Generated on first `db sync push` if not present
schema_id: "550e8400-e29b-41d4-a716-446655440000"

# Database engine (stable, project-level)
# Version is tracked per-snapshot in manifest.yaml
database:
  engine: "PostgreSQL"

# API configuration for web app synchronization
api:
  base_url: "https://api.yourapp.com"
  key: "${BFLOO_API_KEY}"  # Resolved from environment or .env file
```

#### PostgreSQL Environment Configuration

Environment-specific connection parameters following the official PostgreSQL libpq specification. Use environment variables (`${VAR_NAME}`) for sensitive data.

```yaml
environments:
  production:
    host: "${PROD_DB_HOST}"
    port: 5432
    dbname: "${PROD_DB_NAME}"
    user: "${PROD_DB_USER}"
    password: "${PROD_DB_PASSWORD}"
    sslmode: "verify-full"
    sslrootcert: "/etc/ssl/certs/ca-certificates.crt"
    connect_timeout: 10
    application_name: "myapp-prod"

  staging:
    host: "${STAGING_DB_HOST}"
    port: 5432
    dbname: "${STAGING_DB_NAME}"
    user: "${STAGING_DB_USER}"
    password: "${STAGING_DB_PASSWORD}"
    sslmode: "require"
    connect_timeout: 10

  development:
    host: "localhost"
    port: 5432
    dbname: "myapp_dev"
    user: "postgres"
    password: "${DEV_DB_PASSWORD}"
    sslmode: "prefer"
```

**PostgreSQL Connection Parameters:**

| Parameter | Required | Description |
|-----------|----------|-------------|
| `host` | Yes | Hostname, IP, or Unix socket path. Comma-separated for multiple hosts. |
| `dbname` | Yes | Database name |
| `user` | Yes | PostgreSQL username |
| `port` | No | Port number (default: 5432) |
| `password` | No | Password (use env vars!) |
| `sslmode` | No | SSL mode: `disable`, `allow`, `prefer`, `require`, `verify-ca`, `verify-full` |
| `sslcert` | No | Path to client SSL certificate |
| `sslkey` | No | Path to client SSL private key |
| `sslrootcert` | No | Path to CA certificate, or `system` for system CAs |
| `connect_timeout` | No | Connection timeout in seconds |
| `application_name` | No | Application name (visible in pg_stat_activity) |
| `target_session_attrs` | No | Session type: `any`, `read-write`, `read-only`, `primary`, `standby` |
| `load_balance_hosts` | No | Load balancing: `disable`, `random` |

See the full schema in `docs/schemas/project/config/engines/postgresql.json` for all supported parameters including SSL, GSS/Kerberos, and TCP keepalive options.

**Required fields (base):**

- `database.engine` - Database engine name (e.g., "PostgreSQL")

**Required fields (per environment):**

- `host` - Database host
- `dbname` - Database name
- `user` - Database user

**Optional fields:**

- `schema_id` - UUID linking to web application (generated on first push if not present)
- `api.base_url` - Custom API endpoint (defaults to production)

---

### 2. `schema.yaml` - Working Schema

The active schema file. **Clean format with no metadata** - no IDs, no snapshot information, no timestamps, no database version.

```yaml
name: "E-commerce Platform"
description: "Main database schema for the e-commerce platform"

tables:
  - name: users
    description: "User accounts and authentication data"
    columns:
      - name: id
        type: serial
        description: "Primary key"
        constraints:
          nullable: false
      - name: username
        type: text
        description: "Unique username for login"
        constraints:
          nullable: false
          min_length:
            name: "min_username_length"
            value: 3
          max_length:
            name: "max_username_length"
            value: 50
      - name: email
        type: text
        constraints:
          nullable: false
          max_length:
            name: "max_email_length"
            value: 255
      - name: is_active
        type: boolean
        description: "Whether the account is active"
        default: true
        constraints:
          nullable: false
      - name: created_at
        type: timestamp
        description: "Account creation timestamp"
        default: "current_timestamp"
        constraints:
          nullable: false
    constraints:
      - name: "pk_users"
        type: primary_key
        columns: ["id"]
      - name: "unique_username"
        type: unique
        columns: ["username"]
      - name: "unique_email"
        type: unique
        columns: ["email"]

  - name: orders
    description: "Customer orders"
    columns:
      - name: id
        type: serial
        constraints:
          nullable: false
      - name: user_id
        type: integer
        description: "Reference to user who placed the order"
        constraints:
          nullable: false
      - name: total_cents
        type: integer
        description: "Order total in cents"
        constraints:
          nullable: false
          min_value:
            name: "min_order_total"
            value: 0
      - name: status
        type: text
        default: "pending"
        constraints:
          nullable: false
          max_length:
            name: "max_status_length"
            value: 20
      - name: created_at
        type: timestamp
        default: "current_timestamp"
        constraints:
          nullable: false
    constraints:
      - name: "pk_orders"
        type: primary_key
        columns: ["id"]
      - name: "fk_orders_user"
        type: foreign_key
        columns: ["user_id"]
        references:
          table: "users"
          columns: ["id"]
        on_delete: "cascade"
        on_update: "no_action"
```

**Schema structure:**

- `name` - Human-readable schema name (required, max 64 chars)
- `description` - Schema description (optional, max 256 chars)
- `tables` - Array of table definitions

**Table structure:**

- `name` - Table name (required, pattern: `^[a-z][a-z0-9_]*$`, max 63 chars)
- `description` - Table description (optional, max 256 chars)
- `columns` - Array of column definitions
- `constraints` - Array of table-level constraints (PKs, FKs, unique)

**Column structure:**

- `name` - Column name (required, pattern: `^[a-z][a-z0-9_]*$`, max 63 chars)
- `type` - Data type (required, enum: `text`, `integer`, `serial`, `boolean`, `date`, `timestamp`)
- `description` - Column description (optional, max 256 chars)
- `default` - Default value (optional, type-dependent)
- `constraints` - Column-level constraints

**Supported column types:**

| Type        | Default values allowed           |
| ----------- | -------------------------------- |
| `text`      | Any string, `null`               |
| `integer`   | Any integer, `null`              |
| `serial`    | Not allowed (auto-generated)     |
| `boolean`   | `true`, `false`, `null`          |
| `date`      | `"current_date"`, `null`         |
| `timestamp` | `"current_timestamp"`, `null`    |

**Column constraints:**

- `nullable` - Boolean, whether column allows NULL (default: true)
- `min_length` / `max_length` - For text columns (object with `name` and `value`)
- `min_value` / `max_value` - For integer columns (object with `name` and `value`)

**Table-level constraints:**

- `primary_key` - Primary key constraint
- `unique` - Unique constraint
- `foreign_key` - Foreign key constraint (requires `references`, `on_delete`, `on_update`)

**Foreign key actions (required for foreign_key constraints):**

- `cascade` - Propagate changes
- `set_null` - Set to NULL (column must be nullable)
- `set_default` - Set to default value
- `restrict` - Prevent action
- `no_action` - Deferred check (PostgreSQL default)

---

### 3. `_history_/manifest.yaml` - Snapshot Registry

Tracks all snapshots with their metadata, including database version per snapshot. This is the **only place** where snapshot IDs, parent relationships, timestamps, and database versions are stored.

```yaml
# Currently active snapshot label
current: "v3.0.0"

# Ordered list of snapshots (oldest first)
snapshots:
  - label: "v1.0.0"
    id: "123e4567-e89b-12d3-a456-426614174000"
    parent_id: null
    database_version: "15.0"
    created_at: "2024-01-15T10:30:00"
    file: "2024-01-15_v1.0.0.yaml"
    synced: true

  - label: "v2.0.0"
    id: "987fcdeb-51d2-43a1-b123-456789abcdef"
    parent_id: "123e4567-e89b-12d3-a456-426614174000"
    database_version: "15.0"
    created_at: "2024-03-20T14:45:00"
    file: "2024-03-20_v2.0.0.yaml"
    synced: true

  - label: "v2.1.0-hotfix"
    id: "aaa11111-2222-3333-4444-555566667777"
    parent_id: "987fcdeb-51d2-43a1-b123-456789abcdef"
    database_version: "15.0"
    created_at: "2024-04-01T08:00:00"
    file: "2024-04-01_v2.1.0-hotfix.yaml"
    synced: true

  - label: "v3.0.0"
    id: "456def78-9abc-45e6-f789-012345678901"
    parent_id: "987fcdeb-51d2-43a1-b123-456789abcdef"
    database_version: "16.0"
    created_at: "2024-05-15T09:20:00"
    file: "2024-05-15_v3.0.0.yaml"
    synced: false
```

**Manifest fields:**

- `current` - Label of the currently active snapshot
- `snapshots` - Array of snapshot metadata

**Snapshot metadata:**

- `label` - Human-readable version label (required, unique, max 64 chars)
- `id` - UUID for the snapshot (generated by CLI)
- `parent_id` - UUID of parent snapshot (`null` for initial snapshot)
- `database_version` - Database engine version for this snapshot (e.g., "15.0", "16.0")
- `created_at` - ISO 8601 timestamp
- `file` - Filename in `_history_/` directory
- `synced` - Boolean, whether snapshot has been pushed to web app

**Database version tracking:**

The `database_version` field allows tracking database engine upgrades between snapshots. When generating migrations, the CLI uses this to:

- Apply version-specific SQL syntax
- Warn about potential incompatibilities
- Handle new features introduced in newer versions

**Snapshot tree structure:**

Snapshots form a tree via `parent_id` relationships. Multiple snapshots can share the same parent (branching).

```
v1.0.0 (PostgreSQL 15.0)
├── v2.0.0 (PostgreSQL 15.0)
│   ├── v2.1.0-hotfix (PostgreSQL 15.0)
│   └── v3.0.0 (PostgreSQL 16.0) ← current
└── v1.1.0-experiment (PostgreSQL 15.0)
```

---

### 4. `_history_/*.yaml` - Snapshot Files

Immutable copies of `schema.yaml` at each snapshot point. **Identical format to `schema.yaml`** - clean, no metadata.

Filename format: `YYYY-MM-DD_<label>.yaml`

Examples:

- `2024-01-15_v1.0.0.yaml`
- `2024-03-20_v2.0.0.yaml`
- `2024-04-01_v2.1.0-hotfix.yaml`

---

## CLI Commands

### Project Initialization

```bash
# Initialize a new database project
db init

# Creates:
# - config.yaml (with prompts for engine)
# - schema.yaml (empty template)
# - _history_/ directory
# - _history_/manifest.yaml (empty)
```

### Snapshot Management

```bash
# Create a snapshot from current schema.yaml
db snapshot create --label "v1.0.0" --database-version "15.0"

# Workflow:
# 1. Validates label doesn't exist in manifest
# 2. Generates UUID for snapshot
# 3. Sets parent_id from manifest.current (null if first snapshot)
# 4. Copies schema.yaml to _history_/YYYY-MM-DD_<label>.yaml
# 5. Adds entry to manifest.yaml with synced: false
# 6. Updates manifest.current to new label

# List all snapshots
db snapshot list

# Output (tree view):
# v1.0.0 [synced] (PostgreSQL 15.0)
# ├── v2.0.0 [synced] (PostgreSQL 15.0)
# │   ├── v2.1.0-hotfix [synced] (PostgreSQL 15.0)
# │   └── v3.0.0 [local] (PostgreSQL 16.0) ← current
# └── v1.1.0-experiment [local] (PostgreSQL 15.0)

# Show snapshot details
db snapshot show v2.0.0

# Switch to a different snapshot (updates schema.yaml)
db snapshot checkout v2.0.0

# Rename a snapshot (useful for conflict resolution)
db snapshot rename v3.0.0 v3.0.1
```

### Synchronization

```bash
# Push local snapshots to web application
db sync push

# Workflow:
# 1. Authenticates via API key (from env var)
# 2. Registers schema_id if not exists (first push)
# 3. Pushes all snapshots where synced: false
# 4. Server validates labels are unique
# 5. On success, marks snapshots as synced: true
# 6. On label conflict, suggests renaming

# Pull snapshots from web application
db sync pull --to "v3.0.0"

# Workflow:
# 1. Fetches snapshot tree from API
# 2. Downloads linear history from root to target snapshot
# 3. Saves snapshot files to _history_/
# 4. Updates manifest.yaml
# 5. Updates schema.yaml to target snapshot
# 6. Updates manifest.current

# Interactive pull (shows tree selector if --to not provided)
db sync pull

# Output:
# Fetching snapshot tree...
#
# v1.0.0 (PostgreSQL 15.0)
# ├── v2.0.0 (PostgreSQL 15.0)
# │   ├── v2.1.0-hotfix (PostgreSQL 15.0)
# │   └── v3.0.0 (PostgreSQL 16.0) ← latest
# └── v1.1.0-experiment (PostgreSQL 15.0)
#
# ? Select snapshot to pull: [v3.0.0]
```

### Migrations

Migrations are generated on-the-fly by diffing snapshots. **No SQL files are stored** - the CLI generates and executes SQL at runtime.

The CLI tracks which snapshot each database instance is at using an internal `_snapshot_history_` table in the database itself.

```bash
# Migrate database to a specific snapshot
db migrate --to v3.0.0 --env development

# Workflow:
# 1. Connects to database using environment connection string
# 2. Queries _snapshot_history_ table to get current snapshot
# 3. Calculates path from current to target snapshot
# 4. Generates sequential migrations for each step
# 5. Executes all migrations in a single transaction (atomic)
# 6. Updates _snapshot_history_ table on success
# 7. Full rollback on any failure

# Preview migrations without executing (dry-run)
db migrate --to v3.0.0 --env development --preview

# Output:
# Current: v1.0.0 (PostgreSQL 15.0)
# Target: v3.0.0 (PostgreSQL 16.0)
#
# Migration path: v1.0.0 → v2.0.0 → v3.0.0
#
# Step 1: v1.0.0 → v2.0.0
# ========================
# -- Add column 'phone' to 'users'
# ALTER TABLE users ADD COLUMN phone TEXT;
#
# -- Add table 'products'
# CREATE TABLE products (
#   id SERIAL NOT NULL,
#   name TEXT NOT NULL,
#   ...
# );
#
# Step 2: v2.0.0 → v3.0.0
# ========================
# -- Modify column 'email' in 'users'
# ALTER TABLE users ALTER COLUMN email TYPE VARCHAR(320);
# ...

# Alternative flag name for preview
db migrate --to v3.0.0 --env development --plan

# Rollback (down migration) - just specify an earlier snapshot
db migrate --to v1.0.0 --env development

# Workflow for rollback:
# 1. Detects target is ancestor of current (down migration)
# 2. Generates reverse migrations for each step
# 3. Executes atomically
```

**Migration path calculation:**

For non-linear trees, the CLI calculates the path through the common ancestor:

```
Current: v2.1.0-hotfix
Target: v3.0.0

Tree:
v1.0.0
├── v2.0.0
│   ├── v2.1.0-hotfix ← current
│   └── v3.0.0 ← target

Path: v2.1.0-hotfix → v2.0.0 (down) → v3.0.0 (up)
```

**Sequential generation, atomic execution:**

- Migrations are generated step-by-step respecting each snapshot's database version
- All migrations execute in a single transaction
- If any step fails, entire migration rolls back to original state
- Database is never left in intermediate state

### Validation

```bash
# Validate schema.yaml against specification
db validate

# Output:
# ✓ Schema structure valid
# ✓ All table names valid
# ✓ All column types valid
# ✓ All constraints valid
# ✓ Foreign key references valid

# Validate with specific database version
db validate --database-version "16.0"
```

### Diff

```bash
# Show diff between two snapshots
db diff v2.0.0 v3.0.0

# Output:
# Database version: 15.0 → 16.0
#
# Tables added: payments
# Tables removed: (none)
# Tables modified: users, orders
#
# users:
#   + column: phone (text, nullable)
#   ~ column: email (max_length: 255 → 320)
#
# orders:
#   + column: shipping_address (text, nullable)

# Diff current schema.yaml against a snapshot
db diff v2.0.0

# Diff current schema.yaml against current manifest snapshot
db diff
```

---

## Database Tracking

The CLI maintains a `_snapshot_history_` table in each database instance to track migration state. This is internal and users don't interact with it directly.

**Purpose:**

- Know which snapshot the database is currently at
- Enable `--from` auto-detection (no need to specify manually)
- Track migration history for auditing

**Table structure (internal, subject to change):**

```sql
CREATE TABLE _snapshot_history_ (
  id SERIAL PRIMARY KEY,
  snapshot_id UUID NOT NULL,
  snapshot_label VARCHAR(64) NOT NULL,
  applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  direction VARCHAR(4) NOT NULL CHECK (direction IN ('up', 'down'))
);
```

---

## API Synchronization

### Authentication

API key-based authentication. Configure in `config.yaml`:

```yaml
api:
  key: "${BFLOO_API_KEY}"
```

The CLI resolves the environment variable at runtime (see [Environment Variable Resolution](#environment-variable-resolution) below).

---

## Environment Variable Resolution

The CLI supports environment variable references in configuration values using `${VAR_NAME}` syntax. This keeps sensitive data out of committed files while maintaining explicit configuration.

### Supported Locations

Environment variables can be used in:

- `config.yaml` - API key, any string value
- Engine config (e.g., PostgreSQL environments) - passwords, hosts, usernames

### Syntax

```yaml
# Full value from env var
api:
  key: "${BFLOO_API_KEY}"

# Mixed with literal text
environments:
  production:
    application_name: "myapp-${DEPLOYMENT_ENV}"
```

### Resolution Order

When the CLI encounters a `${VAR_NAME}` reference, it resolves the value from:

1. **System environment** - Variables already set in the shell
2. **`.env` file** - If not found in system environment, searched in:
   - Same directory as the config file being processed
   - Project root (directory containing `.git`)
   - Current working directory

The first `.env` file found is used. Variables in `.env` do not override system environment variables.

### CLI Override

```bash
# Specify a custom .env file location
db sync push --env-file /path/to/.env.production

# This overrides the automatic .env file search
db migrate --to v2.0.0 --env production --env-file ~/.secrets/prod.env
```

### Error Handling

- **Missing variable**: CLI fails with error message indicating which variable is missing
- **Malformed syntax**: `${` without closing `}` is treated as literal text
- **Empty value**: Resolved to empty string (valid, but may cause downstream errors)

### Security Best Practices

1. **Never commit `.env` files** - Add to `.gitignore`
2. **Use descriptive variable names** - `PROD_DB_PASSWORD` not `PASSWORD`
3. **Document required variables** - List in project README
4. **Use different variables per environment** - `DEV_DB_PASSWORD`, `PROD_DB_PASSWORD`

### Example `.env` File

```bash
# .env (git-ignored)
BFLOO_API_KEY=sk_live_abc123...

# Database credentials
DEV_DB_PASSWORD=localdevpass
STAGING_DB_PASSWORD=staging_secret_here
PROD_DB_PASSWORD=production_secret_here
PROD_DB_HOST=prod-db.example.com
```

### API Endpoints (Conceptual)

```
POST   /api/schemas                    # Register new schema (first push)
GET    /api/schemas/:schema_id         # Get schema metadata
GET    /api/schemas/:schema_id/tree    # Get snapshot tree
POST   /api/schemas/:schema_id/snapshots       # Push new snapshot
GET    /api/schemas/:schema_id/snapshots/:id   # Get snapshot content
```

### Conflict Resolution

**Label conflicts:**

When pushing a snapshot with a label that already exists on the server:

1. CLI receives 409 Conflict response
2. CLI displays error: `Label "v3.0.0" already exists. Please rename your snapshot.`
3. User runs: `db snapshot rename v3.0.0 v3.0.1`
4. User retries: `db sync push`

**Parent ID conflicts:**

Multiple snapshots can share the same parent (this is valid - it's branching). No conflict resolution needed.

---

## Schema Validation Rules

### PostgreSQL Specific Rules

1. **Column types:** `text`, `integer`, `serial`, `boolean`, `date`, `timestamp`

2. **Serial columns:**

   - Cannot have explicit default values
   - Can be nullable (though unusual)

3. **Date columns:**

   - Default: only `"current_date"` or `null`

4. **Timestamp columns:**

   - Default: only `"current_timestamp"` or `null`

5. **Boolean columns:**

   - Default: `true`, `false`, or `null`

6. **Integer columns:**

   - Default: any integer or `null`
   - min_value/max_value constraints use integer type

7. **Text columns:**

   - Default: any string or `null`
   - min_length/max_length constraints use integer type
   - No VARCHAR/CHAR - use TEXT with length constraints instead

8. **Foreign keys:**

   - `on_delete` and `on_update` are **required**
   - Valid actions: `cascade`, `set_null`, `set_default`, `restrict`, `no_action`

9. **Naming conventions:**

   - Pattern: `^[a-z][a-z0-9_]*$`
   - Max length: 63 characters (PostgreSQL identifier limit)

10. **Descriptions:**

    - Optional on tables, columns, constraints
    - Max length: 256 characters

11. **Default + Nullable rules:**

    - If `default: null`, then `nullable` must be `true`
    - If `nullable: false`, then `default` cannot be `null`

---

## Migration from Current JSON Format

The current examples use JSON with embedded snapshot metadata. Migration path:

1. Extract `schema.tables` + `schema.name` + `schema.description` → `schema.yaml`
2. Extract `schema.snapshot` + `database.version` → `_history_/manifest.yaml`
3. Extract `database.engine` → `config.yaml`
4. Move `schema.id` → `config.yaml` as `schema_id`

**Before (JSON with metadata):**

```json
{
  "database": { "engine": "PostgreSQL", "version": "15.0" },
  "schema": {
    "id": "550e8400-...",
    "name": "E-commerce",
    "snapshot": {
      "id": "123e4567-...",
      "label": "v1.0.0",
      "parent_id": null,
      "created_at": "2024-01-15T10:30:00"
    },
    "tables": [...]
  }
}
```

**After (YAML, clean separation):**

`config.yaml`:

```yaml
schema_id: "550e8400-..."
database:
  engine: "PostgreSQL"
```

`schema.yaml`:

```yaml
name: "E-commerce"
description: null
tables:
  - ...
```

`_history_/manifest.yaml`:

```yaml
current: "v1.0.0"
snapshots:
  - label: "v1.0.0"
    id: "123e4567-..."
    parent_id: null
    database_version: "15.0"
    created_at: "2024-01-15T10:30:00"
    file: "2024-01-15_v1.0.0.yaml"
    synced: true
```

---

## Down Migrations

Down migrations (rollbacks) work by reversing the migration path:

```bash
# Current database: v3.0.0
# Target: v1.0.0

db migrate --to v1.0.0 --env development
```

The CLI:

1. Detects this is a rollback (target is ancestor of current)
2. Calculates reverse path: v3.0.0 → v2.0.0 → v1.0.0
3. Generates reverse SQL for each step (e.g., `DROP COLUMN` for columns that were added)
4. Executes atomically

**Destructive operations:**

Down migrations may involve destructive operations (dropping columns/tables with data). Handling of this is TBD - options include:

- Require `--force` flag
- Interactive confirmation
- Warning but proceed

---

## Future Considerations

1. **GitHub App Integration** - Direct commit/PR creation from web app
2. **Branch conventions** - Formal branch support beyond tree structure
3. **Schema diffing in web app** - Visual diff between snapshots
4. **Multiple database support** - Different engines in same project
5. **Schema linting** - Best practice suggestions beyond validation
6. **Migration hooks** - Pre/post migration scripts
7. **Seed data management** - Track seed/fixture data alongside schema
