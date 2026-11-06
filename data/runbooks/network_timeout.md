# Runbook #201 — Network Timeout and Connectivity Issues

**Category**: Network / Infrastructure  
**Severity**: MEDIUM to HIGH  
**Typical MTTR**: 5–20 minutes

---

## Symptoms
- HTTP 504 Gateway Timeout
- TCP connection refused errors
- DNS resolution failures
- Intermittent connectivity between microservices
- Load balancer health checks failing

---

## Diagnostic Steps

### Step 1 — Test Service Connectivity
```bash
# From the affected service pod
kubectl exec -it <pod-name> -n production -- /bin/sh

# Test DNS resolution
nslookup <target-service>
dig <target-service>.production.svc.cluster.local

# Test TCP connectivity
nc -zv <target-host> <port>
curl -v --max-time 5 http://<target-service>/health
```

### Step 2 — Check Network Policies
```bash
# List Kubernetes Network Policies
kubectl get networkpolicies -n production

# Describe a specific policy
kubectl describe networkpolicy <policy-name> -n production
```

### Step 3 — Check Load Balancer / Ingress
```bash
# Check ingress controller logs
kubectl logs -n ingress-nginx -l app.kubernetes.io/name=ingress-nginx --tail=100

# Check service endpoints
kubectl get endpoints <service-name> -n production
```

---

## Common Fixes

| Issue | Fix |
|---|---|
| DNS not resolving | Restart CoreDNS: `kubectl rollout restart deployment/coredns -n kube-system` |
| NetworkPolicy blocking traffic | Update policy to allow required pod selectors |
| No healthy endpoints | Check pod readiness probes and ensure pods are Running |
| Timeout too short | Increase timeout in nginx/envoy config |

---

## Verification
- Confirm `curl -f http://<service>/health` returns HTTP 200
- Confirm inter-service calls succeed with normal latency
