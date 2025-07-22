# Airflow Demo Project

This project demonstrates Apache Airflow configuration and setup using Docker Compose with custom configurations and persistent data storage.

## Overview

Apache Airflow is an open-source platform to develop, schedule, and monitor workflows. This demo project showcases various Airflow configurations, best practices, and includes a complete Docker-based setup with:

- **Custom webserver configuration** with RBAC and authentication
- **Persistent PostgreSQL database** with local volume mounting
- **Easy-to-use management script** for common operations
- **Production-ready setup** with proper volume mounts and configurations

## Quick Start

### Prerequisites

- Docker and Docker Compose installed
- At least 4GB of RAM available
- At least 2 CPU cores recommended
- At least 10GB of free disk space

### Getting Started

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd airflowdemo
   ```

2. **Initialize Airflow (first time only)**
   ```bash
   ./run.sh init
   ```

3. **Start Airflow services**
   ```bash
   ./run.sh up
   ```

4. **Access Airflow Web UI**
   - URL: http://localhost:8080
   - Default credentials: `admin` / `admin`

5. **Stop services when done**
   ```bash
   ./run.sh down
   ```

## Management Script (`run.sh`)

The project includes a convenient shell script for managing your Airflow setup:

### Available Commands

| Command | Description |
|---------|-------------|
| `./run.sh` or `./run.sh up` | Start Airflow services |
| `./run.sh down` | Stop and remove services |
| `./run.sh restart` | Restart all services |
| `./run.sh logs` | Show logs from all services |
| `./run.sh status` | Show status of all services |
| `./run.sh init` | Initialize Airflow (run first time) |
| `./run.sh clean` | Clean up everything (containers, volumes, networks) |
| `./run.sh help` | Show help message |

### Script Features

- ✅ **Automatic setup** - Creates necessary directories
- ✅ **Environment handling** - Sets AIRFLOW_UID automatically
- ✅ **Docker validation** - Checks if Docker is running
- ✅ **Colored output** - Easy-to-read status messages
- ✅ **Safety prompts** - Confirmation for destructive operations

## Architecture

### Services

The Docker Compose setup includes the following services:

- **airflow-webserver** - Web UI and API server
- **airflow-scheduler** - Task scheduler
- **airflow-dag-processor** - DAG processing
- **airflow-worker** - Celery worker for task execution
- **airflow-triggerer** - Trigger management
- **postgres** - Database backend with persistent storage
- **redis** - Message broker for Celery

### Volume Mounts

| Local Path | Container Path | Purpose |
|------------|----------------|----------|
| `./dags` | `/opt/airflow/dags` | DAG files |
| `./logs` | `/opt/airflow/logs` | Airflow logs |
| `./config` | `/opt/airflow/config` | Configuration files |
| `./plugins` | `/opt/airflow/plugins` | Custom plugins |
| `./webserver_config.py` | `/opt/airflow/webserver_config.py` | Webserver configuration |
| `./pg_data` | `/var/lib/postgresql/data` | PostgreSQL data (persistent) |

## Project Structure

```
airflowdemo/
├── docker-compose.yaml          # Docker Compose configuration
├── run.sh                       # Management script
├── webserver_config.py          # Airflow webserver configuration
├── README.md                    # This file
├── .gitignore                   # Git ignore rules
├── dags/                        # DAG files directory
├── logs/                        # Airflow logs directory
├── config/                      # Configuration files
├── plugins/                     # Custom plugins
├── pg_data/                     # PostgreSQL data (auto-created)
└── images/                      # Documentation images
    ├── RBAC-Config.png
    ├── APIPermission.png
    ├── AppRole.png
    ├── EnterpriseAppAssignRole.png
    └── TokenConfiguration.png
```

## Configuration

### RBAC Configuration

The project includes Role-Based Access Control (RBAC) configuration for Airflow:

![RBAC Configuration](images/RBAC-Config.png)

### API Permissions

API permission configuration:

![API Permission](images/APIPermission.png)

### Application Roles

Application role setup:

![App Role](images/AppRole.png)

### Enterprise App Role Assignment

Enterprise application role assignment:

![Enterprise App Assign Role](images/EnterpriseAppAssignRole.png)

### Token Configuration

Token configuration settings:

![Token Configuration](images/TokenConfiguration.png)

## Development

### Adding DAGs

1. Place your DAG files in the `dags/` directory
2. DAGs will be automatically detected and loaded by Airflow
3. Use the web UI to monitor and trigger your DAGs

### Custom Plugins

1. Add custom operators, hooks, or sensors to the `plugins/` directory
2. Follow Airflow plugin development guidelines
3. Restart services to load new plugins: `./run.sh restart`

### Configuration Changes

- **Airflow configuration**: Edit files in the `config/` directory
- **Webserver settings**: Modify `webserver_config.py`
- **Docker settings**: Update `docker-compose.yaml`
- **Environment variables**: Edit `.env` file

## Troubleshooting

### Common Issues

#### 1. Permission Issues
```bash
# Fix file permissions
sudo chown -R $USER:$USER .
./run.sh init
```

#### 2. Port Already in Use
```bash
# Check what's using port 8080
lsof -i :8080

# Kill the process or change port in docker-compose.yaml
```

#### 3. Database Connection Issues
```bash
# Clean and reinitialize
./run.sh clean
./run.sh init
./run.sh up
```

#### 4. Memory Issues
```bash
# Check Docker memory allocation
docker system df
docker system prune -f
```

### Logs and Debugging

```bash
# View all service logs
./run.sh logs

# View specific service logs
docker-compose logs airflow-webserver
docker-compose logs postgres

# Follow logs in real-time
docker-compose logs -f airflow-scheduler
```

## Security Considerations

### Production Deployment

⚠️ **Important**: This setup is for development/demo purposes. For production:

1. **Change default credentials**
2. **Use secure passwords** for database and Redis
3. **Enable HTTPS** with proper SSL certificates
4. **Configure proper authentication** (LDAP, OAuth, etc.)
5. **Set up proper network security**
6. **Use secrets management** for sensitive data
7. **Enable audit logging**

### Environment Variables

Create a `.env` file for environment-specific settings:

```bash
# .env file example
AIRFLOW_UID=1000
AIRFLOW__CORE__FERNET_KEY=your-fernet-key-here
AIRFLOW__WEBSERVER__SECRET_KEY=your-secret-key-here
```

## Backup and Recovery

### Database Backup

```bash
# Backup PostgreSQL data
docker-compose exec postgres pg_dump -U airflow airflow > backup.sql

# Or backup the entire pg_data directory
tar -czf pg_data_backup.tar.gz pg_data/
```

### Restore Database

```bash
# Restore from SQL dump
docker-compose exec -T postgres psql -U airflow airflow < backup.sql

# Or restore pg_data directory
./run.sh down
rm -rf pg_data/
tar -xzf pg_data_backup.tar.gz
./run.sh up
```

## Performance Tuning

### Resource Allocation

Adjust resource limits in `docker-compose.yaml`:

```yaml
services:
  airflow-webserver:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '0.5'
```

### Database Optimization

- Monitor database performance with `./run.sh logs postgres`
- Consider using connection pooling for high-load scenarios
- Regular database maintenance and cleanup

## Monitoring

### Health Checks

```bash
# Check service health
./run.sh status

# Check individual service health
docker-compose ps
curl http://localhost:8080/health
```

### Metrics and Logging

- Airflow logs are available in the `logs/` directory
- Use the web UI for task monitoring and debugging
- Consider integrating with external monitoring tools

## Configuration Details

### RBAC Configuration

The project includes Role-Based Access Control (RBAC) configuration for Airflow:

![RBAC Configuration](images/RBAC-Config.png)

### API Permissions

API permission configuration:

![API Permission](images/APIPermission.png)

### Application Roles

Application role setup:

![App Role](images/AppRole.png)

### Enterprise App Role Assignment

Enterprise application role assignment:

![Enterprise App Assign Role](images/EnterpriseAppAssignRole.png)

### Token Configuration

Token configuration settings:

![Token Configuration](images/TokenConfiguration.png)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For issues and questions:

- Check the [troubleshooting section](#troubleshooting)
- Review Airflow documentation: https://airflow.apache.org/docs/
- Open an issue in the repository

## Changelog

### v1.0.0
- Initial setup with Docker Compose
- Custom webserver configuration
- Persistent PostgreSQL storage
- Management script for easy operations
- Comprehensive documentation

## Getting Started

1. Ensure Apache Airflow is installed
2. Configure your Airflow settings using the provided configuration files
3. Start the Airflow webserver and scheduler

## Documentation

For more information about Apache Airflow, visit the [official documentation](https://airflow.apache.org/docs/).
