# Runbook #601 — API Rate Limit Breach / DDoS Attack

**Category**: Network / Security  
**Severity**: HIGH to CRITICAL  
**Typical MTTR**: 5–20 minutes  
**Services Affected**: API Gateway, Rate Limiter, any downstream service receiving flood traffic

---

## Symptoms
- Spike in HTTP 429 (Too Many Requests) responses in gateway logs
- Traffic from a single IP or subnet exceeding normal baseline by 5–10x
- Legitimate users experiencing HTTP 503 or extreme latency (>10s)
- Worker thread pools on backend services exhausted
- WAF (Web Application Firewall) triggering volumetric attack rules
- API error rate dashboard showing sharp spike

---

## Root Cause Patterns

| Pattern | Likely Cause |
|---|---|
| Traffic from single /24 subnet | Botnet or scraper coordinated from one CIDR block |
| Traffic targeting one endpoint | Credential stuffing or scraping attack |
| Traffic mimicking legitimate behavior | Sophisticated bot with valid session tokens |
| Traffic spike matching a business event | Flash sale / viral post causing legitimate surge |

---

## Immediate Remediation Steps

### Step 1 — Identify Attacking Source
```bash
# Check top IP addresses by request count in last 10 minutes
# (Assuming Nginx access log format)
awk '{print $1}' /var/log/nginx/access.log | sort | uniq -c | sort -rn | head -20

# Or query your gateway's rate-limiter metrics
curl http://rate-limiter-service:8080/api/v1/stats/top-ips?window=10m
```

### Step 2 — Block Attacking Subnet at WAF/Firewall
```bash
# AWS WAF: Block a CIDR block
aws wafv2 update-ip-set \
  --scope CLOUDFRONT \
  --id <ip-set-id> \
  --addresses "203.0.113.0/24" \
  --lock-token <lock-token>

# Nginx: Immediate block
echo "deny 203.0.113.0/24;" >> /etc/nginx/conf.d/blocklist.conf
nginx -s reload

# iptables (Linux kernel level)
iptables -I INPUT -s 203.0.113.0/24 -j DROP
```

### Step 3 — Tighten Rate Limits
```bash
# Kubernetes: Update rate-limiter configuration
kubectl set env deployment/rate-limiter \
  RATE_LIMIT_REQUESTS_PER_MIN=1000 \
  RATE_LIMIT_BURST=200 \
  -n production

kubectl rollout restart deployment/rate-limiter -n production
```

### Step 4 — Scale Backend Services to Handle Residual Load
```bash
# Scale up search-service to handle legitimate traffic
kubectl scale deployment search-service --replicas=10 -n production
```

---

## Long-Term Fix
1. Implement CAPTCHA for endpoints with high scraping risk
2. Set up Cloudflare / AWS Shield Advanced for DDoS protection
3. Use Bot Management solution (Cloudflare Bot Management, AWS WAF Bot Control)
4. Implement progressive rate limiting: warn → throttle → block
5. Add anomaly detection alerts for traffic 3x above hourly baseline

---

## Verification Steps
- Confirm attacking subnet is fully blocked (no traffic in gateway logs)
- Verify legitimate user error rate returns to baseline (<0.1%)
- Confirm backend service worker queues have drained
- Check HTTP 200 responses are flowing normally
