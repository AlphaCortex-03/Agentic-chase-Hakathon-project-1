# Runbook #301 — Service Restart and Health Verification

**Category**: General Operations  
**Severity**: Any  
**Typical MTTR**: 2–5 minutes

---

## When to Use This Runbook
- Service is unresponsive but no known root cause yet
- Service health check returning 500 or timing out
- After applying a configuration fix that requires a service restart

---

## Restart Procedure

### Kubernetes (Recommended)
```bash
# Rolling restart (zero downtime)
kubectl rollout restart deployment/<service-name> -n production

# Monitor the rollout progress
kubectl rollout status deployment/<service-name> -n production --timeout=120s

# Check pod status
kubectl get pods -l app=<service-name> -n production -w
```

### Docker Compose
```bash
docker-compose restart <service-name>
docker-compose ps
```

---

## Health Verification After Restart
```bash
# HTTP health check
curl -f http://<service-host>:<port>/health || echo "UNHEALTHY"
curl -f http://<service-host>:<port>/ready  || echo "NOT READY"

# Check recent logs
kubectl logs -l app=<service-name> -n production --since=2m --tail=50
```

---

## Escalation
If the service does not become healthy within 5 minutes of restart, escalate to Runbook #401 (DB), #501 (Memory), or #601 (Network) based on the error type observed in logs.
