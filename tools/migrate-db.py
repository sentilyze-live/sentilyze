#!/usr/bin/env python3
"""
Database Migration Utility for Sentilyze

This script handles database migrations for PostgreSQL using a simple
migration system. Supports running migrations, checking status, and rollback.

Usage:
    python migrate-db.py --environment <env> migrate
    python migrate-db.py --environment <env> status
    python migrate-db.py --environment <env> rollback 1
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
except ImportError:
    print("Error: psycopg2 is required. Install with: pip install psycopg2-binary")
    sys.exit(1)


# Default migration directory
MIGRATIONS_DIR = Path(__file__).parent.parent / "migrations"

# Migration tracking table schema
MIGRATION_TABLE_SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_migrations (
    id SERIAL PRIMARY KEY,
    version VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(255) NOT NULL,
    checksum VARCHAR(64) NOT NULL,
    applied_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    execution_time_ms INTEGER,
    success BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE INDEX IF NOT EXISTS idx_schema_migrations_version 
    ON schema_migrations(version);
"""


class DatabaseMigration:
    """Database migration manager."""
    
    def __init__(self, database_url: str, migrations_dir: Path = MIGRATIONS_DIR):
        self.database_url = database_url
        self.migrations_dir = migrations_dir
        self.connection = None
        
        # Ensure migrations directory exists
        self.migrations_dir.mkdir(parents=True, exist_ok=True)
    
    def connect(self) -> bool:
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(self.database_url)
            self.connection.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            return True
        except Exception as e:
            print(f"✗ Failed to connect to database: {e}")
            return False
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def init_migration_table(self) -> bool:
        """Initialize the migration tracking table."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(MIGRATION_TABLE_SCHEMA)
            print("✓ Migration tracking table initialized")
            return True
        except Exception as e:
            print(f"✗ Failed to initialize migration table: {e}")
            return False
    
    def get_applied_migrations(self) -> List[dict]:
        """Get list of already applied migrations."""
        try:
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "SELECT version, name, checksum, applied_at, success "
                    "FROM schema_migrations ORDER BY applied_at"
                )
                rows = cursor.fetchall()
                return [
                    {
                        "version": row[0],
                        "name": row[1],
                        "checksum": row[2],
                        "applied_at": row[3],
                        "success": row[4],
                    }
                    for row in rows
                ]
        except Exception as e:
            print(f"Warning: Could not read applied migrations: {e}")
            return []
    
    def get_available_migrations(self) -> List[Tuple[str, Path]]:
        """Get list of available migration files."""
        if not self.migrations_dir.exists():
            return []
        
        migrations = []
        for file_path in sorted(self.migrations_dir.glob("*.sql")):
            # Extract version from filename (e.g., 001_initial_schema.sql)
            version = file_path.stem.split("_")[0]
            migrations.append((version, file_path))
        
        return migrations
    
    def calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA-256 checksum of migration file."""
        with open(file_path, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    def apply_migration(self, version: str, file_path: Path) -> bool:
        """Apply a single migration."""
        print(f"\nApplying migration: {file_path.name}")
        
        try:
            # Read migration file
            with open(file_path, 'r') as f:
                migration_sql = f.read()
            
            # Calculate checksum
            checksum = self.calculate_checksum(file_path)
            
            # Execute migration
            start_time = time.time()
            
            with self.connection.cursor() as cursor:
                cursor.execute(migration_sql)
            
            execution_time = int((time.time() - start_time) * 1000)
            
            # Record migration
            with self.connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO schema_migrations (version, name, checksum, execution_time_ms, success)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (version, file_path.name, checksum, execution_time, True)
                )
            
            print(f"✓ Migration applied successfully ({execution_time}ms)")
            return True
            
        except Exception as e:
            print(f"✗ Migration failed: {e}")
            
            # Record failed migration
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO schema_migrations (version, name, checksum, success)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (version) DO UPDATE SET success = FALSE
                        """,
                        (version, file_path.name, "", False)
                    )
            except Exception:
                pass
            
            return False
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        print(f"\nRolling back migration: {version}")
        
        # Look for rollback file
        rollback_file = self.migrations_dir / f"{version}_rollback.sql"
        
        if not rollback_file.exists():
            print(f"✗ Rollback file not found: {rollback_file}")
            return False
        
        try:
            # Read rollback file
            with open(rollback_file, 'r') as f:
                rollback_sql = f.read()
            
            # Execute rollback
            with self.connection.cursor() as cursor:
                cursor.execute(rollback_sql)
            
            # Remove migration record
            with self.connection.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM schema_migrations WHERE version = %s",
                    (version,)
                )
            
            print(f"✓ Migration rolled back successfully")
            return True
            
        except Exception as e:
            print(f"✗ Rollback failed: {e}")
            return False
    
    def migrate(self) -> bool:
        """Run all pending migrations."""
        print("Running database migrations...")
        print("=" * 60)
        
        # Initialize migration table
        if not self.init_migration_table():
            return False
        
        # Get applied and available migrations
        applied = {m["version"]: m for m in self.get_applied_migrations()}
        available = self.get_available_migrations()
        
        if not available:
            print("No migration files found")
            return True
        
        # Find pending migrations
        pending = [
            (version, path) for version, path in available 
            if version not in applied
        ]
        
        if not pending:
            print("✓ Database is up to date")
            return True
        
        print(f"Found {len(pending)} pending migration(s)")
        
        # Apply pending migrations
        all_success = True
        for version, file_path in pending:
            if not self.apply_migration(version, file_path):
                all_success = False
                break
        
        return all_success
    
    def status(self) -> bool:
        """Show migration status."""
        print("Migration Status")
        print("=" * 60)
        
        # Initialize migration table if needed
        self.init_migration_table()
        
        # Get applied and available migrations
        applied = {m["version"]: m for m in self.get_applied_migrations()}
        available = self.get_available_migrations()
        
        if not available:
            print("No migration files found in:", self.migrations_dir)
            return True
        
        print(f"\n{'Version':<15} {'Status':<12} {'Applied At':<25} {'Name'}")
        print("-" * 80)
        
        for version, file_path in available:
            if version in applied:
                migration = applied[version]
                status = "Applied" if migration["success"] else "Failed"
                applied_at = migration["applied_at"].strftime("%Y-%m-%d %H:%M:%S")
                print(f"{version:<15} {status:<12} {applied_at:<25} {file_path.name}")
            else:
                print(f"{version:<15} {'Pending':<12} {'N/A':<25} {file_path.name}")
        
        pending_count = len(available) - len(applied)
        print(f"\n{len(applied)} applied, {pending_count} pending")
        
        return True
    
    def rollback(self, count: int = 1) -> bool:
        """Rollback the last N migrations."""
        print(f"Rolling back {count} migration(s)...")
        print("=" * 60)
        
        # Get applied migrations
        applied = self.get_applied_migrations()
        
        if not applied:
            print("No migrations to rollback")
            return True
        
        # Get last N successful migrations
        successful = [m for m in applied if m["success"]]
        to_rollback = successful[-count:]
        
        if not to_rollback:
            print("No successful migrations to rollback")
            return True
        
        print(f"Will rollback {len(to_rollback)} migration(s):")
        for m in to_rollback:
            print(f"  - {m['version']}: {m['name']}")
        
        # Confirm rollback
        if input("\nContinue? (yes/no): ").lower() != "yes":
            print("Rollback cancelled")
            return True
        
        # Rollback in reverse order
        all_success = True
        for migration in reversed(to_rollback):
            if not self.rollback_migration(migration["version"]):
                all_success = False
                break
        
        return all_success
    
    def create_migration(self, name: str) -> bool:
        """Create a new migration file."""
        # Get next version number
        available = self.get_available_migrations()
        
        if available:
            last_version = available[-1][0]
            try:
                next_version = int(last_version) + 1
            except ValueError:
                next_version = len(available) + 1
        else:
            next_version = 1
        
        version = f"{next_version:03d}"
        filename = f"{version}_{name}.sql"
        file_path = self.migrations_dir / filename
        
        # Create migration template
        template = f"""-- Migration: {name}
-- Version: {version}
-- Created: {datetime.now().isoformat()}

-- Write your migration SQL here


-- Rollback SQL (save as {version}_rollback.sql)
-- Write your rollback SQL here
"""
        
        with open(file_path, 'w') as f:
            f.write(template)
        
        print(f"✓ Created migration: {file_path}")
        print(f"  Remember to create {version}_rollback.sql for rollback support")
        
        return True


def get_database_url(environment: str) -> str:
    """Get database URL from environment or configuration."""
    # Try environment variable first
    env_var = f"DATABASE_URL_{environment.upper()}"
    if env_var in os.environ:
        return os.environ[env_var]
    
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]
    
    # Default local database
    if environment == "local":
        return "postgresql://sentilyze:sentilyze@localhost:5432/sentilyze"
    
    raise ValueError(f"No database URL configured for environment: {environment}")


def main():
    parser = argparse.ArgumentParser(
        description="Database Migration Utility for Sentilyze",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python migrate-db.py --environment dev migrate
  python migrate-db.py --environment dev status
  python migrate-db.py --environment dev rollback 1
  python migrate-db.py --environment dev create add_user_table
        """
    )
    
    parser.add_argument(
        "--environment",
        required=True,
        choices=["local", "dev", "staging", "prod"],
        help="Environment to run migrations against"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (overrides environment variable)"
    )
    parser.add_argument(
        "--migrations-dir",
        type=Path,
        default=MIGRATIONS_DIR,
        help="Path to migrations directory"
    )
    
    parser.add_argument(
        "command",
        choices=["migrate", "status", "rollback", "create"],
        help="Migration command to execute"
    )
    parser.add_argument(
        "args",
        nargs="*",
        help="Additional arguments for the command"
    )
    
    args = parser.parse_args()
    
    # Get database URL
    try:
        database_url = args.database_url or get_database_url(args.environment)
    except ValueError as e:
        print(f"Error: {e}")
        sys.exit(1)
    
    # Initialize migration manager
    migrator = DatabaseMigration(database_url, args.migrations_dir)
    
    print("=" * 60)
    print("Sentilyze Database Migration")
    print(f"Environment: {args.environment}")
    print(f"Migrations: {args.migrations_dir}")
    print("=" * 60)
    
    # Connect to database
    if not migrator.connect():
        sys.exit(1)
    
    try:
        # Execute command
        success = False
        
        if args.command == "migrate":
            success = migrator.migrate()
        
        elif args.command == "status":
            success = migrator.status()
        
        elif args.command == "rollback":
            count = int(args.args[0]) if args.args else 1
            success = migrator.rollback(count)
        
        elif args.command == "create":
            if not args.args:
                print("Error: Migration name required")
                sys.exit(1)
            name = args.args[0]
            success = migrator.create_migration(name)
        
        # Final status
        print("\n" + "=" * 60)
        if success:
            print("✓ Command completed successfully")
            print("=" * 60)
            sys.exit(0)
        else:
            print("✗ Command failed")
            print("=" * 60)
            sys.exit(1)
    
    finally:
        migrator.disconnect()


if __name__ == "__main__":
    main()
