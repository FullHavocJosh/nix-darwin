---
name: k8s-manifest-generator
description: Create production-ready Kubernetes manifests for Deployments, Services, ConfigMaps, and Secrets following best practices and security standards. Use when generating Kubernetes YAML manifests, creating K8s resources, or implementing production-grade Kubernetes configurations.
---

# Kubernetes Manifest Generator

Step-by-step guidance for creating production-ready Kubernetes manifests including Deployments, Services, ConfigMaps, Secrets, and PersistentVolumeClaims.

## When to Use This Skill

- Create new Kubernetes Deployment manifests
- Define Service resources for network connectivity
- Generate ConfigMap and Secret resources
- Create PersistentVolumeClaim manifests for stateful workloads
- Follow Kubernetes best practices and naming conventions
- Implement resource limits, health checks, and security contexts

## Deployment Manifest

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: <app-name>
  namespace: <namespace>
  labels:
    app.kubernetes.io/name: <app-name>
    app.kubernetes.io/version: "1.0.0"
    app.kubernetes.io/managed-by: kubectl
spec:
  replicas: 3
  selector:
    matchLabels:
      app: <app-name>
  template:
    metadata:
      labels:
        app: <app-name>
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/port: "9090"
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: <container-name>
          image: <image>:<tag> # Never use :latest
          ports:
            - containerPort: <port>
              name: http
          resources:
            requests:
              memory: "256Mi"
              cpu: "250m"
            limits:
              memory: "512Mi"
              cpu: "500m"
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /ready
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities:
              drop:
                - ALL
          envFrom:
            - configMapRef:
                name: <app-name>-config
            - secretRef:
                name: <app-name>-secret
```

## Service Manifest

```yaml
# ClusterIP (internal)
apiVersion: v1
kind: Service
metadata:
  name: <app-name>
  namespace: <namespace>
spec:
  type: ClusterIP
  selector:
    app: <app-name>
  ports:
    - name: http
      port: 80
      targetPort: 8080
```

## ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: <app-name>-config
  namespace: <namespace>
data:
  APP_MODE: production
  LOG_LEVEL: info
  app.properties: |
    server.port=8080
    logging.level=INFO
```

## Secret

> **Warning:** Never hardcode credentials in manifests. Replace all placeholder values before use and store actual secrets in a secrets manager (e.g., Vault, AWS Secrets Manager) or use sealed-secrets/external-secrets.

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: <app-name>-secret
  namespace: <namespace>
type: Opaque
stringData:
  DATABASE_PASSWORD: "<replace-with-actual-password>" # MUST be replaced before use
  API_KEY: "<replace-with-actual-api-key>" # MUST be replaced before use
```

## PersistentVolumeClaim

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: <app-name>-data
  namespace: <namespace>
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path # Use appropriate StorageClass
  resources:
    requests:
      storage: 10Gi
```

## Organization Patterns

**Kustomize structure (recommended for homelab):**

```
base/
├── kustomization.yaml
├── deployment.yaml
├── service.yaml
└── configmap.yaml
overlays/
├── dev/
│   └── kustomization.yaml
└── prod/
    └── kustomization.yaml
```

## Validation

```bash
# Dry-run validation
kubectl apply -f manifest.yaml --dry-run=client
kubectl apply -f manifest.yaml --dry-run=server

# Lint
kube-score score manifest.yaml
kube-linter lint manifest.yaml
```

## Best Practices

1. **Always set resource requests and limits** — prevents resource starvation
2. **Implement both liveness and readiness probes** — Kubernetes can manage lifecycle
3. **Use specific image tags** — never `:latest`
4. **Apply security contexts** — run as non-root, drop capabilities
5. **Use ConfigMaps and Secrets** — separate config from code
6. **Label everything** — use standard `app.kubernetes.io/*` labels
7. **Validate before applying** — use dry-run
8. **Store in Git** — version control all manifests
