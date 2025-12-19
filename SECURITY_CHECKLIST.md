# Security Checklist for Production Deployment

## Before Deploying to Cloud Run ✅

- [ ] **Secrets Management**
  - [ ] All sensitive values moved to GCP Secret Manager
  - [ ] `SECRET_KEY` is a strong, randomly generated value
  - [ ] Database password is strong and unique
  - [ ] `.env` file is in `.gitignore` and never committed
  - [ ] No hardcoded API keys or credentials in code

- [ ] **Code Review**
  - [ ] No logging of sensitive data (passwords, tokens, PII)
  - [ ] SQL injection prevention verified (using ORM/parameterized queries)
  - [ ] XSS prevention in frontend (using Vue templating)
  - [ ] CSRF tokens present for state-changing operations
  - [ ] Authentication/Authorization checks on all protected endpoints

- [ ] **Configuration**
  - [ ] `SEED_DEFAULT_USERS=false` in production
  - [ ] `BACKEND_CORS_ORIGINS` limited to actual frontend domain
  - [ ] Debug mode disabled in production
  - [ ] Database connections use SSL/TLS
  - [ ] HTTP redirects to HTTPS configured

- [ ] **Infrastructure**
  - [ ] Cloud SQL instance has automated backups enabled
  - [ ] Cloud SQL backups are stored securely (geo-replicated)
  - [ ] Cloud Run service account has minimal required IAM roles
  - [ ] Service-to-service communication uses private ingress
  - [ ] VPC connector used for private database access (optional but recommended)
  - [ ] DDoS protection enabled (if applicable)

- [ ] **Monitoring & Logging**
  - [ ] Cloud Logging is enabled and monitoring critical errors
  - [ ] Log retention policy is set appropriately (e.g., 30 days)
  - [ ] Alerts configured for high error rates, timeouts, quota limits
  - [ ] Failed authentication attempts are logged
  - [ ] SQL injection/XSS attempt patterns are monitored

- [ ] **Compliance**
  - [ ] GDPR requirements met (if applicable)
  - [ ] Data retention policies defined and automated
  - [ ] User data deletion capability implemented
  - [ ] Terms of Service and Privacy Policy available
  - [ ] Audit logs maintained for compliance

- [ ] **Testing**
  - [ ] Security tests pass (see `test_*.py` files)
  - [ ] Load testing completed to ensure scalability
  - [ ] Penetration testing performed (if required)
  - [ ] API rate limiting tested

## Ongoing Operations ✅

- [ ] **Regular Updates**
  - [ ] Python dependencies updated monthly
  - [ ] Node.js dependencies updated monthly
  - [ ] Security patches applied immediately
  - [ ] GCP SDK and tools kept up-to-date

- [ ] **Monitoring**
  - [ ] Review logs weekly for suspicious activity
  - [ ] Monitor Cloud SQL query performance
  - [ ] Check Cloud Run error rates and latency
  - [ ] Verify backup integrity

- [ ] **Incident Response**
  - [ ] Incident response plan documented
  - [ ] Contact list for security incidents
  - [ ] Rollback procedure tested
  - [ ] Data breach notification process ready

## Resources

- [GCP Security Best Practices](https://cloud.google.com/security/best-practices)
- [OWASP Top 10](https://owasp.org/www-project-top-ten/)
- [Cloud SQL Security](https://cloud.google.com/sql/docs/postgres/security)
- [Cloud Run Security](https://cloud.google.com/run/docs/security)
