# Runbook #401 — PostgreSQL / MySQL Connection Pool Exhaustion

**Category**: Database Failure  
**Severity**: CRITICAL  
**Typical MTTR**: 5–15 minutes  
**Services Affected**: Any microservice that connects to this database cluster

---

## Symptoms
- `FATAL: too many connections` in DB logs
- Application logs showing `Cannot acquire connection after Nms timeout`
- API endpoints returning HTTP 503 or HTTP 504
- Connection pool utilization metrics at 100%
- Increased thread wait times on application servers
- Cascading failures in downstream services

---

## Root Cause Patterns

| Pattern | Likely Cause |
|---|---|
| Gradual ramp-up over hours | Connection leak in application code (connections not released in `finally` block) |
| Sudden spike at a specific time | Scheduled batch job opening too many parallel connections |
| Correlated with deployment | New code version removed proper connection closing |
| Correlated with traffic spike | Pool size too small for peak load |

---

## Immediate Remediation Steps

### Step 1 — Identify and Kill Idle/Leaked Connections
```sql
-- PostgreSQL: Find all idle connections older than 5 minutes
SELECT pid, usename, application_name, state, 
       now() - state_change AS idle_duration, query
FROM pg_stat_activity
WHERE state = 'idle'
  AND state_change < NOW() - INTERVAL '5 minutes'
ORDER BY idle_duration DESC;

-- Kill specific idle connection
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE state = 'idle'
  AND state_change < NOW() - INTERVAL '5 minutes';
```

### Step 2 — Set Connection Idle Timeout (Temporary Fix)
```sql
-- PostgreSQL: Set TCP idle timeout (apply to postgresql.conf)
ALTER SYSTEM SET tcp_keepalives_idle = 60;
ALTER SYSTEM SET tcp_keepalives_interval = 10;
ALTER SYSTEM SET tcp_keepalives_count = 6;
SELECT pg_reload_conf();
```

### Step 3 — Temporarily Increase Pool Size (If Not at DB Max)
```bash
# Update application environment variable (Kubernetes)
kubectl set env deployment/auth-service DB_POOL_MAX_SIZE=150 -n production

# Trigger rolling restart to pick up new config
kubectl rollout restart deployment/auth-service -n production
```

### Step 4 — Verify Pool Drain
```bash
# Monitor active connection count in real-time
watch -n 2 'psql -h $DB_HOST -U $DB_USER -c "SELECT count(*) FROM pg_stat_activity WHERE state != '"'"'idle'"'"';"'
```

---

## Long-Term Fix
1. Enable `pgBouncer` connection pooler in front of the database
2. Add connection leak detection in application (e.g., HikariCP `leakDetectionThreshold`)
3. Set `statement_timeout` and `idle_in_transaction_session_timeout` in PostgreSQL config
4. Add a Prometheus alert when pool utilization exceeds 80%

---

## Verification Steps
- Check that pool utilization drops below 50%
- Confirm API health checks return HTTP 200
- Verify downstream services (payment-gateway, etc.) recover
- Check error rate drops to baseline in Grafana dashboard
