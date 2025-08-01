# Deployment Guide

This guide covers deploying the Ultravox-Twilio Integration Service in various environments.

## Quick Deployment Options

| Method | Best For | Complexity | Scalability |
|--------|----------|------------|-------------|
| [Docker Compose](#docker-compose) | Small deployments, testing | Low | Limited |
| [Docker Swarm](#docker-swarm) | Medium deployments | Medium | Good |
| [Kubernetes](#kubernetes) | Large deployments, enterprise | High | Excellent |
| [Systemd Service](#systemd-service) | Single server, simple setup | Low | Limited |

## Environment Configuration

### Environment Files

The service supports multiple environment configurations:

- **`.env.development`**: Development settings with debug enabled
- **`.env.production`**: Production settings with security hardened
- **`.env.staging`**: Staging environment (create as needed)

### Required Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `ULTRAVOX_API_KEY` | Ultravox API authentication key | `sk-1234567890abcdef` |
| `TWILIO_ACCOUNT_SID` | Twilio Account SID | `ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` |
| `TWILIO_AUTH_TOKEN` | Twilio authentication token | `your_auth_token_here` |
| `TWILIO_PHONE_NUMBER` | Twilio phone number for calls | `+1234567890` |

### Optional Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `json` | Log format (json, console) |
| `HOST` | `0.0.0.0` | Host to bind the server |
| `PORT` | `8000` | Port to run the server |
| `WORKERS` | `1` | Number of worker processes |
| `CORS_ORIGINS` | `*` | Allowed CORS origins (comma-separated) |
| `MAX_CONTENT_LENGTH` | `1048576` | Maximum request size in bytes |
| `RATE_LIMIT_PER_MINUTE` | `60` | Rate limit per minute |
| `RATE_LIMIT_PER_HOUR` | `1000` | Rate limit per hour |
| `RATE_LIMIT_BURST` | `10` | Burst rate limit |

## Docker Compose

### Basic Deployment

1. **Prepare environment:**
   ```bash
   cp .env.production .env
   # Edit .env with your actual values
   ```

2. **Deploy:**
   ```bash
   docker-compose up -d
   ```

3. **Verify deployment:**
   ```bash
   curl http://localhost:8000/api/v1/health
   ```

### Production Docker Compose

```yaml
version: '3.8'

services:
  ultravox-twilio-service:
    image: ultravox-twilio-service:latest
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
      - LOG_FORMAT=json
      - ULTRAVOX_API_KEY=${ULTRAVOX_API_KEY}
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
      - TWILIO_PHONE_NUMBER=${TWILIO_PHONE_NUMBER}
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - app-network

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - ultravox-twilio-service
    networks:
      - app-network
    profiles:
      - production

networks:
  app-network:
    driver: bridge
```

### Using the Deployment Script

```bash
# Deploy to production
./scripts/deploy.sh

# Deploy to staging
./scripts/deploy.sh --environment staging

# Build only (no deployment)
./scripts/deploy.sh --build-only

# Skip tests
./scripts/deploy.sh --skip-tests
```

## Docker Swarm

### Initialize Swarm

```bash
# On manager node
docker swarm init

# On worker nodes (use token from init command)
docker swarm join --token <token> <manager-ip>:2377
```

### Deploy Stack

```yaml
# docker-stack.yml
version: '3.8'

services:
  ultravox-twilio-service:
    image: ultravox-twilio-service:latest
    ports:
      - "8000:8000"
    environment:
      - DEBUG=false
      - LOG_LEVEL=INFO
      - ULTRAVOX_API_KEY=${ULTRAVOX_API_KEY}
      - TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
      - TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
      - TWILIO_PHONE_NUMBER=${TWILIO_PHONE_NUMBER}
    deploy:
      replicas: 3
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3
      update_config:
        parallelism: 1
        delay: 10s
        failure_action: rollback
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
        reservations:
          cpus: '0.25'
          memory: 256M
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/api/v1/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - app-network

networks:
  app-network:
    driver: overlay
```

```bash
# Deploy stack
docker stack deploy -c docker-stack.yml ultravox-twilio

# Check status
docker stack services ultravox-twilio

# Scale service
docker service scale ultravox-twilio_ultravox-twilio-service=5
```

## Kubernetes

### Namespace and ConfigMap

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: ultravox-twilio
---
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: ultravox-twilio-config
  namespace: ultravox-twilio
data:
  DEBUG: "false"
  LOG_LEVEL: "INFO"
  LOG_FORMAT: "json"
  HOST: "0.0.0.0"
  PORT: "8000"
  CORS_ORIGINS: "https://yourdomain.com"
```

### Secret

```yaml
# k8s/secret.yaml
apiVersion: v1
kind: Secret
metadata:
  name: ultravox-twilio-secrets
  namespace: ultravox-twilio
type: Opaque
data:
  ULTRAVOX_API_KEY: <base64-encoded-key>
  TWILIO_ACCOUNT_SID: <base64-encoded-sid>
  TWILIO_AUTH_TOKEN: <base64-encoded-token>
  TWILIO_PHONE_NUMBER: <base64-encoded-number>
```

### Deployment

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ultravox-twilio-service
  namespace: ultravox-twilio
spec:
  replicas: 3
  selector:
    matchLabels:
      app: ultravox-twilio-service
  template:
    metadata:
      labels:
        app: ultravox-twilio-service
    spec:
      containers:
      - name: ultravox-twilio-service
        image: ultravox-twilio-service:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: ultravox-twilio-config
        - secretRef:
            name: ultravox-twilio-secrets
        livenessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/v1/health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          limits:
            cpu: 500m
            memory: 512Mi
          requests:
            cpu: 250m
            memory: 256Mi
```

### Service and Ingress

```yaml
# k8s/service.yaml
apiVersion: v1
kind: Service
metadata:
  name: ultravox-twilio-service
  namespace: ultravox-twilio
spec:
  selector:
    app: ultravox-twilio-service
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8000
  type: ClusterIP
---
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: ultravox-twilio-ingress
  namespace: ultravox-twilio
  annotations:
    nginx.ingress.kubernetes.io/rewrite-target: /
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - api.yourdomain.com
    secretName: ultravox-twilio-tls
  rules:
  - host: api.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: ultravox-twilio-service
            port:
              number: 80
```

### Deploy to Kubernetes

```bash
# Apply all configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods -n ultravox-twilio

# View logs
kubectl logs -f deployment/ultravox-twilio-service -n ultravox-twilio

# Scale deployment
kubectl scale deployment ultravox-twilio-service --replicas=5 -n ultravox-twilio
```

## Systemd Service

### Create Service File

```ini
# /etc/systemd/system/ultravox-twilio.service
[Unit]
Description=Ultravox-Twilio Integration Service
After=network.target

[Service]
Type=exec
User=ultravox
Group=ultravox
WorkingDirectory=/opt/ultravox-twilio
Environment=PATH=/opt/ultravox-twilio/.venv/bin
EnvironmentFile=/opt/ultravox-twilio/.env
ExecStart=/opt/ultravox-twilio/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=5
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Install and Start

```bash
# Create user
sudo useradd -r -s /bin/false ultravox

# Install application
sudo mkdir -p /opt/ultravox-twilio
sudo chown ultravox:ultravox /opt/ultravox-twilio

# Copy application files
sudo cp -r . /opt/ultravox-twilio/
sudo chown -R ultravox:ultravox /opt/ultravox-twilio/

# Install service
sudo systemctl daemon-reload
sudo systemctl enable ultravox-twilio
sudo systemctl start ultravox-twilio

# Check status
sudo systemctl status ultravox-twilio
```

## Load Balancing

### Nginx Configuration

```nginx
# /etc/nginx/sites-available/ultravox-twilio
upstream ultravox_twilio {
    least_conn;
    server 127.0.0.1:8000 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8001 max_fails=3 fail_timeout=30s;
    server 127.0.0.1:8002 max_fails=3 fail_timeout=30s;
}

server {
    listen 80;
    server_name api.yourdomain.com;
    
    # Redirect HTTP to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;
    
    # SSL configuration
    ssl_certificate /etc/ssl/certs/yourdomain.com.crt;
    ssl_certificate_key /etc/ssl/private/yourdomain.com.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512:ECDHE-RSA-AES256-GCM-SHA384:DHE-RSA-AES256-GCM-SHA384;
    ssl_prefer_server_ciphers off;
    
    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload";
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://ultravox_twilio;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
        
        # Health check
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503 http_504;
    }
    
    # Health check endpoint (bypass rate limiting)
    location /api/v1/health {
        limit_req off;
        proxy_pass http://ultravox_twilio;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## Monitoring and Logging

### Health Checks

```bash
# Basic health check
curl -f http://localhost:8000/api/v1/health

# Detailed health check
curl -f http://localhost:8000/api/v1/health/detailed
```

### Log Management

#### Centralized Logging with ELK Stack

```yaml
# docker-compose.logging.yml
version: '3.8'

services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.5.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data

  logstash:
    image: docker.elastic.co/logstash/logstash:8.5.0
    volumes:
      - ./logstash.conf:/usr/share/logstash/pipeline/logstash.conf
    ports:
      - "5044:5044"
    depends_on:
      - elasticsearch

  kibana:
    image: docker.elastic.co/kibana/kibana:8.5.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch

volumes:
  elasticsearch_data:
```

#### Log Rotation

```bash
# /etc/logrotate.d/ultravox-twilio
/opt/ultravox-twilio/logs/*.log {
    daily
    missingok
    rotate 30
    compress
    delaycompress
    notifempty
    create 644 ultravox ultravox
    postrotate
        systemctl reload ultravox-twilio
    endscript
}
```

## Security Considerations

### Firewall Configuration

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw deny 8000/tcp   # Block direct access to app
sudo ufw enable
```

### SSL/TLS Configuration

```bash
# Generate SSL certificate with Let's Encrypt
sudo certbot --nginx -d api.yourdomain.com

# Auto-renewal
sudo crontab -e
# Add: 0 12 * * * /usr/bin/certbot renew --quiet
```

### Environment Security

1. **Never commit `.env` files to version control**
2. **Use secrets management in production**
3. **Rotate API keys regularly**
4. **Enable audit logging**
5. **Use least privilege access**

## Backup and Recovery

### Database Backup (if applicable)

```bash
# Backup script
#!/bin/bash
BACKUP_DIR="/opt/backups/ultravox-twilio"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup configuration
cp /opt/ultravox-twilio/.env $BACKUP_DIR/env_$DATE

# Backup logs
tar -czf $BACKUP_DIR/logs_$DATE.tar.gz /opt/ultravox-twilio/logs/

# Clean old backups (keep 30 days)
find $BACKUP_DIR -name "*.tar.gz" -mtime +30 -delete
```

### Disaster Recovery

1. **Document all configuration**
2. **Maintain infrastructure as code**
3. **Test recovery procedures regularly**
4. **Keep offline backups of critical data**

## Performance Tuning

### Application Tuning

```bash
# Multiple workers for production
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4

# Or use gunicorn
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
```

### System Tuning

```bash
# Increase file descriptor limits
echo "* soft nofile 65536" >> /etc/security/limits.conf
echo "* hard nofile 65536" >> /etc/security/limits.conf

# Optimize network settings
echo "net.core.somaxconn = 65536" >> /etc/sysctl.conf
echo "net.ipv4.tcp_max_syn_backlog = 65536" >> /etc/sysctl.conf
sysctl -p
```

## Troubleshooting

### Common Issues

1. **Service won't start:**
   ```bash
   # Check configuration
   python scripts/validate-config.py --env production --strict
   
   # Check logs
   journalctl -u ultravox-twilio -f
   ```

2. **High memory usage:**
   ```bash
   # Monitor memory
   docker stats ultravox-twilio-service
   
   # Adjust worker count
   # Reduce workers if memory constrained
   ```

3. **External API failures:**
   ```bash
   # Test connectivity
   curl -H "Authorization: Bearer $ULTRAVOX_API_KEY" https://api.ultravox.ai/health
   
   # Check Twilio credentials
   curl -u $TWILIO_ACCOUNT_SID:$TWILIO_AUTH_TOKEN \
        https://api.twilio.com/2010-04-01/Accounts/$TWILIO_ACCOUNT_SID.json
   ```

### Performance Issues

1. **Monitor metrics:**
   ```bash
   curl -H "X-API-Key: your-key" http://localhost:8000/api/v1/metrics
   ```

2. **Check resource usage:**
   ```bash
   htop
   iotop
   nethogs
   ```

3. **Analyze logs:**
   ```bash
   grep "ERROR" /opt/ultravox-twilio/logs/app.log | tail -20
   ```

## Maintenance

### Regular Tasks

1. **Update dependencies:**
   ```bash
   pip list --outdated
   pip install -r requirements.txt --upgrade
   ```

2. **Rotate logs:**
   ```bash
   logrotate -f /etc/logrotate.d/ultravox-twilio
   ```

3. **Monitor disk space:**
   ```bash
   df -h
   du -sh /opt/ultravox-twilio/logs/
   ```

4. **Check service health:**
   ```bash
   systemctl status ultravox-twilio
   curl -f http://localhost:8000/api/v1/health
   ```

### Upgrade Procedure

1. **Backup current version**
2. **Test new version in staging**
3. **Deploy with rolling update**
4. **Verify functionality**
5. **Monitor for issues**

For more detailed troubleshooting, see the [Troubleshooting Guide](troubleshooting.md).