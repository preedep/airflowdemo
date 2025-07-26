# DAG Serialization Fix Script Documentation

## Overview
This script (`fix_dag_serialization.sh`) addresses common DAG serialization issues in Apache Airflow across multiple versions, specifically designed for your Airflow 3.0.2 setup.

## Common Serialization Issues Addressed

### 1. **Python Cache Issues**
- Removes `.pyc` files and `__pycache__` directories
- Clears temporary Airflow DAG cache files

### 2. **Database Serialization Problems**
- Clears serialized DAGs from the database
- Compatible with Airflow 2.x and 3.x

### 3. **Non-Serializable Objects**
- Replaces problematic datetime objects with Pendulum
- Removes heavy imports (pandas, numpy) that can cause issues
- Adds proper imports for serializable objects

### 4. **DAG Validation**
- Syntax checking for all Python files
- Airflow-specific DAG validation

## Usage

### Basic Usage
```bash
# Run complete fix process
./fix_dag_serialization.sh

# Show help
./fix_dag_serialization.sh --help
```

### Advanced Options
```bash
# Create backup only
./fix_dag_serialization.sh --backup-only

# Clear cache only
./fix_dag_serialization.sh --clear-cache

# Validate DAGs only
./fix_dag_serialization.sh --validate-only

# Run without creating backup
./fix_dag_serialization.sh --no-backup
```

## What the Script Does

### 1. **Backup Creation**
- Creates timestamped backup in `dag_backups_YYYYMMDD_HHMMSS/`
- Preserves original DAGs before making changes

### 2. **Cache Clearing**
- Removes Python bytecode files
- Clears Airflow DAG processor cache
- Removes temporary files

### 3. **Code Fixes**
- Replaces `datetime.datetime.now()` with `pendulum.now()`
- Removes problematic imports
- Adds missing imports

### 4. **Database Cleanup**
- Clears serialized DAG table
- Forces re-serialization on next load

### 5. **Service Restart**
- Restarts Docker containers (webserver, scheduler, worker)
- Waits for services to become healthy

### 6. **Validation**
- Checks DAG syntax
- Verifies import errors
- Reviews logs for serialization issues

## Your Airflow Setup Compatibility

✅ **Compatible with your setup:**
- Airflow 3.0.2
- Docker Compose deployment
- CeleryExecutor
- PostgreSQL database
- Multiple DAG directories (`scb_ap1234`, `scb_ap5678`)

## When to Use This Script

### Symptoms of Serialization Issues:
- DAGs not appearing in UI
- "Failed to serialize DAG" errors
- Import errors in DAG processor
- Slow DAG loading
- Version compatibility issues after upgrades

### Common Scenarios:
- After Airflow version upgrade
- When adding new DAGs with complex dependencies
- After modifying existing DAGs
- When DAGs work locally but fail in production

## Troubleshooting

### If Script Fails:
1. Check Docker containers are running: `docker-compose ps`
2. Verify database connectivity
3. Check logs: `docker-compose logs airflow-webserver`
4. Restore from backup if needed

### Manual Checks:
```bash
# Check DAG import errors
docker-compose exec airflow-webserver airflow dags list-import-errors

# Check specific DAG
docker-compose exec airflow-webserver airflow dags check <dag_id>

# View DAG details
docker-compose exec airflow-webserver airflow dags show <dag_id>
```

## Best Practices

### Before Running:
1. Ensure all DAG files are committed to version control
2. Stop any running DAG executions if possible
3. Verify Docker containers are healthy

### After Running:
1. Check Airflow UI for DAG visibility
2. Verify DAG schedules are working
3. Monitor logs for any new errors
4. Test DAG execution

## Integration with Your Project

The script automatically detects:
- Your Docker Compose setup
- Airflow home directory
- DAG directories structure
- Airflow version

It works seamlessly with your existing:
- OAuth configuration
- Role mapping system
- Email templates
- Custom webserver config

## Backup and Recovery

### Automatic Backups:
- Created before any changes
- Timestamped for easy identification
- Full DAG directory copy

### Manual Restore:
```bash
# If issues occur, restore from backup
cp -r dag_backups_YYYYMMDD_HHMMSS/dags/* dags/
docker-compose restart airflow-webserver airflow-scheduler
```

## Monitoring

### Log Locations:
- Script output: Console with colored logging
- Airflow logs: `logs/` directory
- Docker logs: `docker-compose logs`

### Success Indicators:
- ✅ All services restart successfully
- ✅ DAGs appear in UI
- ✅ No import errors
- ✅ DAG serialization completes

## Support

If you encounter issues:
1. Check the backup directory for original files
2. Review Airflow logs for specific errors
3. Use `--validate-only` to check DAG syntax
4. Consider running individual fix components

The script is designed to be safe and reversible, with comprehensive logging to help diagnose any issues.
