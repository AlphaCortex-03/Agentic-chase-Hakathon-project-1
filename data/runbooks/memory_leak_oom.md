# Runbook #501 — JVM Memory Leak and OOM (Out-Of-Memory) Kill

**Category**: Memory / Runtime Failure  
**Severity**: HIGH to CRITICAL  
**Typical MTTR**: 10–30 minutes  
**Services Affected**: Any JVM-based service (Java, Kotlin, Scala)

---

## Symptoms
- `java.lang.OutOfMemoryError: Java heap space` in application logs
- Consecutive Full GC cycles with long pause times (> 2 seconds)
- Pod/container killed with exit code `137` (SIGKILL from OOMKiller)
- Service in `CrashLoopBackOff` state in Kubernetes
- Heap dump file written to disk (`*.hprof`)
- Increasing JVM heap usage trend over time (memory leak signature)

---

## Root Cause Patterns

| Symptom Pattern | Likely Root Cause |
|---|---|
| Heap grows continuously over hours | Object retention / memory leak (unclosed streams, static caches) |
| OOM on startup | Heap limit set too low for the application's baseline memory |
| OOM after specific API calls | Large object allocation without streaming (e.g., loading full DB table into memory) |
| OOM after traffic spike | Insufficient heap for peak concurrent request load |

---

## Immediate Remediation Steps

### Step 1 — Increase JVM Heap Limit (Emergency Fix)
```bash
# Kubernetes: Edit deployment to increase memory limit and JVM heap
kubectl edit deployment user-profile-service -n production

# Add/modify under spec.containers[0].resources:
# resources:
#   requests:
#     memory: "2Gi"
#   limits:
#     memory: "4Gi"

# Also update JVM flags in environment:
kubectl set env deployment/user-profile-service \
  JAVA_OPTS="-Xms1g -Xmx3g -XX:+UseG1GC -XX:MaxGCPauseMillis=200" \
  -n production
```

### Step 2 — Restart Crashed Pod
```bash
# Delete the crashing pod (Kubernetes will recreate it with new config)
kubectl delete pod user-profile-service-6f4d9 -n production

# Monitor rollout
kubectl rollout status deployment/user-profile-service -n production
```

### Step 3 — Analyze the Heap Dump
```bash
# Copy heap dump from pod to local machine
kubectl cp production/user-profile-service-6f4d9:/tmp/heap-dump-20241107.hprof ./heap-dump.hprof

# Analyze with Eclipse Memory Analyzer (MAT) or VisualVM
# Look for: Dominator Tree, Retained Heap, Finalizer Queue
```

### Step 4 — Enable GC Logging for Root Cause
```bash
# Add GC logging flags
kubectl set env deployment/user-profile-service \
  JAVA_OPTS="-Xmx3g -Xlog:gc*:file=/tmp/gc.log:time,uptime:filecount=5,filesize=20m" \
  -n production
```

---

## Long-Term Fix
1. Use a memory profiler (async-profiler, YourKit) to find the leaking object type
2. Enable heap alerting at 80% usage via Prometheus + Alertmanager
3. Set `java.lang.ref.SoftReference` cache size limits
4. Use streaming APIs instead of loading full datasets into memory
5. Implement automatic heap dump capture and upload to S3 for analysis

---

## Verification Steps
- Confirm pod is `Running` and not in `CrashLoopBackOff`
- Verify JVM heap usage stable below 70% over 10 minutes
- Check service HTTP health endpoint returns 200
- Monitor GC pause times are below 500ms
