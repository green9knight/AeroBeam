# AeroBeam Production Deployment Guide

**Version:** 1.0  
**Last Updated:** 2026-06-17

## ⚠️ Pre-Deployment Checklist

Before deploying AeroBeam to production, verify ALL items below:

### Critical Safety Items
- [ ] Legal disclaimer visible on first page load
- [ ] Method status warnings prominently displayed
- [ ] All experimental methods clearly labeled
- [ ] Input validation enabled and tested
- [ ] Error messages sanitized (no stack traces to users)

### Security Items
- [ ] HTTPS enabled and enforced
- [ ] Security headers configured (CSP, X-Frame-Options, etc.)
- [ ] Beta password set (if using password protection)
- [ ] CORS policy reviewed and restricted if needed
- [ ] Rate limiting implemented
- [ ] File upload validation enabled

### Testing Items
- [ ] All unit tests passing (`python -m pytest tests/`)
- [ ] Integration tests completed
- [ ] Load testing performed
- [ ] Browser compatibility verified (Chrome, Firefox, Safari, Edge)
- [ ] Mobile responsiveness tested

### Documentation Items
- [ ] User guide available
- [ ] API documentation complete
- [ ] Assumptions documented in reports
- [ ] Material property sources cited

## Environment Setup

### Required Environment Variables

```bash
# Required for production
PORT=8000                          # Port to bind (Render sets this automatically)
HOST=0.0.0.0                       # Bind to all interfaces

# Optional but recommended
AEROBEAM_BETA_PASSWORD=your-secure-password-here
```

### Python Dependencies

Install all dependencies:

```bash
python -m pip install -r requirements.txt
```

Required packages:
- numpy
- matplotlib
- openpyxl
- xlsxwriter
- pytest (for testing)

## Deployment Options

### Option 1: Render (Recommended for Quick Deploy)

1. **Prepare Repository**
   ```bash
   git add .
   git commit -m "Production ready"
   git push origin main
   ```

2. **Create Render Service**
   - Go to https://render.com
   - Click "New +" → "Blueprint"
   - Connect your GitHub repository
   - Render will detect `render.yaml`

3. **Set Environment Variables**
   - In Render dashboard, go to your service
   - Navigate to "Environment"
   - Add: `AEROBEAM_BETA_PASSWORD` (keep secret!)

4. **Deploy**
   - Render will automatically deploy
   - Health check endpoint: `/healthz`
   - Your app will be at: `https://your-app.onrender.com`

### Option 2: Docker (For Custom Hosting)

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.11-slim
   
   WORKDIR /app
   
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt
   
   COPY . .
   
   EXPOSE 8000
   
   CMD ["python", "web_app.py"]
   ```

2. **Build and Run**
   ```bash
   docker build -t aerobeam .
   docker run -p 8000:8000 \
     -e AEROBEAM_BETA_PASSWORD=your-password \
     aerobeam
   ```

### Option 3: Traditional Server (VPS/Dedicated)

1. **Install Python 3.11+**
   ```bash
   sudo apt update
   sudo apt install python3.11 python3.11-venv
   ```

2. **Setup Application**
   ```bash
   cd /opt
   git clone https://github.com/your-repo/aerobeam.git
   cd aerobeam
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Create Systemd Service**
   
   Create `/etc/systemd/system/aerobeam.service`:
   ```ini
   [Unit]
   Description=AeroBeam Web Service
   After=network.target
   
   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/aerobeam
   Environment="PATH=/opt/aerobeam/.venv/bin"
   Environment="AEROBEAM_BETA_PASSWORD=your-password"
   ExecStart=/opt/aerobeam/.venv/bin/python web_app.py
   Restart=always
   RestartSec=10
   
   [Install]
   WantedBy=multi-user.target
   ```

4. **Enable and Start**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable aerobeam
   sudo systemctl start aerobeam
   sudo systemctl status aerobeam
   ```

5. **Setup Nginx Reverse Proxy**
   
   Create `/etc/nginx/sites-available/aerobeam`:
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;
       
       # Redirect to HTTPS
       return 301 https://$server_name$request_uri;
   }
   
   server {
       listen 443 ssl http2;
       server_name your-domain.com;
       
       ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
       
       # Security headers
       add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
       add_header X-Content-Type-Options "nosniff" always;
       add_header X-Frame-Options "DENY" always;
       add_header X-XSS-Protection "1; mode=block" always;
       
       location / {
           proxy_pass http://127.0.0.1:8000;
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           
           # Timeouts for long analyses
           proxy_read_timeout 300s;
           proxy_connect_timeout 75s;
       }
   }
   ```

6. **Enable Site and Restart Nginx**
   ```bash
   sudo ln -s /etc/nginx/sites-available/aerobeam /etc/nginx/sites-enabled/
   sudo nginx -t
   sudo systemctl restart nginx
   ```

## SSL/TLS Certificate Setup

### Using Let's Encrypt (Free)

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
sudo certbot renew --dry-run  # Test auto-renewal
```

## Monitoring and Logging

### Application Logs

Logs are written to stderr. Capture them:

**Systemd:**
```bash
sudo journalctl -u aerobeam -f
```

**Docker:**
```bash
docker logs -f aerobeam-container
```

### Health Monitoring

Set up monitoring for the `/healthz` endpoint:

```bash
# Simple cron job health check
*/5 * * * * curl -f http://localhost:8000/healthz || systemctl restart aerobeam
```

### Recommended Monitoring Tools
- **Uptime monitoring:** UptimeRobot, Pingdom
- **Error tracking:** Sentry (requires integration)
- **Performance:** New Relic, DataDog (requires integration)

## Backup Strategy

### What to Backup
1. User-uploaded `.aerobeam` files (if storing)
2. Configuration files
3. SSL certificates
4. Application logs (for debugging)

### Backup Script Example
```bash
#!/bin/bash
BACKUP_DIR="/backup/aerobeam"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR
tar -czf $BACKUP_DIR/aerobeam_$DATE.tar.gz \
  /opt/aerobeam \
  /etc/nginx/sites-available/aerobeam \
  /etc/systemd/system/aerobeam.service

# Keep only last 30 days
find $BACKUP_DIR -name "aerobeam_*.tar.gz" -mtime +30 -delete
```

## Security Hardening

### Firewall Configuration

```bash
# Allow only HTTP, HTTPS, and SSH
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
sudo ufw allow http
sudo ufw allow https
sudo ufw enable
```

### Rate Limiting (Nginx)

Add to nginx config:
```nginx
limit_req_zone $binary_remote_addr zone=aerobeam:10m rate=10r/m;

location /api/analyze {
    limit_req zone=aerobeam burst=5 nodelay;
    proxy_pass http://127.0.0.1:8000;
}
```

### Fail2Ban (Optional)

Protect against brute force attacks:
```bash
sudo apt install fail2ban
```

## Performance Optimization

### Python Optimization
- Use production WSGI server (gunicorn) instead of built-in server:
  ```bash
  pip install gunicorn
  gunicorn -w 4 -b 0.0.0.0:8000 web_app:app
  ```

### Nginx Caching
Add to nginx config:
```nginx
location /static/ {
    expires 1y;
    add_header Cache-Control "public, immutable";
}
```

## Troubleshooting

### Common Issues

**Issue:** Port already in use
```bash
# Find process using port 8000
sudo lsof -i :8000
# Kill it
sudo kill -9 <PID>
```

**Issue:** Permission denied
```bash
# Fix ownership
sudo chown -R www-data:www-data /opt/aerobeam
```

**Issue:** Module not found
```bash
# Reinstall dependencies
source .venv/bin/activate
pip install -r requirements.txt --force-reinstall
```

**Issue:** Analysis timeout
- Increase `num_points` limit in validation
- Increase nginx `proxy_read_timeout`
- Add progress indicators

### Debug Mode

For debugging (NOT for production):
```python
# In web_app.py, temporarily add:
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Scaling Considerations

### Horizontal Scaling
- Use load balancer (nginx, HAProxy)
- Deploy multiple instances
- Share session state via Redis

### Vertical Scaling
- Increase server resources
- Optimize numpy operations
- Cache common calculations

## Maintenance

### Regular Tasks
- [ ] Weekly: Review logs for errors
- [ ] Monthly: Update dependencies
- [ ] Monthly: Review security advisories
- [ ] Quarterly: Load testing
- [ ] Yearly: SSL certificate renewal (auto with Let's Encrypt)

### Update Procedure
```bash
cd /opt/aerobeam
git pull origin main
source .venv/bin/activate
pip install -r requirements.txt --upgrade
sudo systemctl restart aerobeam
```

## Support and Contact

For production issues:
1. Check logs: `sudo journalctl -u aerobeam -n 100`
2. Verify health: `curl http://localhost:8000/healthz`
3. Review recent changes: `git log -5`
4. Contact: [your-support-email]

## Legal and Compliance

### Required Notices
- Disclaimer must be visible on first page load
- Method status must be accessible
- No warranty statement must be clear
- User assumes all risk

### Data Privacy
- No user data is stored by default
- Beta password is not logged
- Analysis inputs are not persisted
- Comply with local data protection laws

## Post-Deployment Verification

After deployment, verify:

```bash
# Health check
curl https://your-domain.com/healthz
# Expected: "ok"

# Defaults endpoint
curl https://your-domain.com/api/defaults
# Expected: JSON with defaults

# SSL grade
# Visit: https://www.ssllabs.com/ssltest/
# Target: A or A+ rating
```

## Emergency Procedures

### Service Down
```bash
sudo systemctl status aerobeam
sudo systemctl restart aerobeam
sudo journalctl -u aerobeam -n 50
```

### High CPU Usage
```bash
top -u www-data
# If analysis stuck, restart service
sudo systemctl restart aerobeam
```

### Disk Full
```bash
df -h
# Clean old logs
sudo journalctl --vacuum-time=7d
```

## Conclusion

This guide covers production deployment of AeroBeam. Remember:
- **Safety first:** Disclaimer and warnings are critical
- **Security:** HTTPS, headers, validation
- **Monitoring:** Watch logs and health
- **Updates:** Keep dependencies current

For questions or issues, refer to:
- `PRODUCTION_READINESS_AUDIT.md` - Known issues
- `docs/AEROSPACE_STANDARDS_MATRIX.md` - Method validation status
- `README.md` - Basic usage

---
**Document Version:** 1.0  
**Last Review:** 2026-06-17  
**Next Review:** 2026-09-17