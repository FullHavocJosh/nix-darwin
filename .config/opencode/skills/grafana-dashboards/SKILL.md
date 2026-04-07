---
name: grafana-dashboards
description: Create and manage production Grafana dashboards for real-time visualization of system and application metrics. Use when building monitoring dashboards, visualizing metrics, or creating operational observability interfaces.
---

# Grafana Dashboards

Create and manage production-ready Grafana dashboards for comprehensive system observability.

## When to Use This Skill

- Visualize Prometheus metrics for homelab/K8s
- Create custom infrastructure dashboards
- Implement SLO/SLA dashboards
- Monitor Kubernetes workloads

## Dashboard Design Principles

### Information Hierarchy

```
┌─────────────────────────────────────┐
│  Critical Metrics (Stat panels)     │
├─────────────────────────────────────┤
│  Key Trends (Time Series)           │
├─────────────────────────────────────┤
│  Detailed Metrics (Tables/Heatmaps) │
└─────────────────────────────────────┘
```

### RED Method (Services)

- **Rate** — requests per second
- **Errors** — error rate percentage
- **Duration** — latency/response time (P50, P95, P99)

### USE Method (Resources)

- **Utilization** — % time resource is busy
- **Saturation** — queue length/wait time
- **Errors** — error count

## Panel Types

### Stat Panel (Single Value)

```json
{
  "type": "stat",
  "title": "Error Rate",
  "targets": [{ "expr": "job:http_requests_error_rate:percentage" }],
  "fieldConfig": {
    "defaults": {
      "thresholds": {
        "mode": "absolute",
        "steps": [
          { "value": 0, "color": "green" },
          { "value": 5, "color": "yellow" },
          { "value": 10, "color": "red" }
        ]
      },
      "unit": "percent"
    }
  }
}
```

### Time Series Graph

```json
{
  "type": "timeseries",
  "title": "CPU Usage",
  "targets": [
    {
      "expr": "instance:node_cpu:utilization",
      "legendFormat": "{{instance}}"
    }
  ],
  "fieldConfig": {
    "defaults": { "unit": "percent", "min": 0, "max": 100 }
  }
}
```

### Table Panel

```json
{
  "type": "table",
  "title": "Service Status",
  "targets": [{ "expr": "up", "format": "table", "instant": true }],
  "transformations": [
    {
      "id": "organize",
      "options": {
        "excludeByName": { "Time": true },
        "renameByName": {
          "instance": "Instance",
          "job": "Service",
          "Value": "Status"
        }
      }
    }
  ]
}
```

## Template Variables

```json
{
  "templating": {
    "list": [
      {
        "name": "namespace",
        "type": "query",
        "datasource": "Prometheus",
        "query": "label_values(kube_pod_info, namespace)",
        "refresh": 1
      },
      {
        "name": "service",
        "type": "query",
        "datasource": "Prometheus",
        "query": "label_values(kube_service_info{namespace=\"$namespace\"}, service)",
        "refresh": 1,
        "multi": true
      }
    ]
  }
}
```

Use in queries: `sum(rate(http_requests_total{namespace="$namespace", service=~"$service"}[5m]))`

## Common Dashboard Patterns

### Infrastructure Dashboard Panels

- CPU utilization per node
- Memory usage per node
- Disk I/O and utilization
- Network traffic (in/out)
- Pod count by namespace
- Node status (up/down)

### Kubernetes Dashboard Panels

- Pod restart count
- Container resource usage vs limits
- PV/PVC usage
- Deployment replica status
- Ingress request rate

### Application Dashboard Panels

- Request rate (req/s)
- Error rate (%)
- Response time percentiles (P50/P95/P99)
- Active connections
- Cache hit rate

## Dashboard as Code

### Terraform Provisioning

```hcl
resource "grafana_dashboard" "infrastructure" {
  config_json = file("${path.module}/dashboards/infrastructure.json")
  folder      = grafana_folder.monitoring.id
}

resource "grafana_folder" "monitoring" {
  title = "Homelab Monitoring"
}
```

### Ansible Provisioning

```yaml
- name: Deploy Grafana dashboards
  copy:
    src: "{{ item }}"
    dest: /etc/grafana/dashboards/
  with_fileglob:
    - "dashboards/*.json"
  notify: restart grafana
```

### Dashboard Provisioning Config

```yaml
# /etc/grafana/provisioning/dashboards/dashboards.yml
apiVersion: 1
providers:
  - name: "default"
    orgId: 1
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/dashboards
```

## Best Practices

1. **Start with community templates** — Grafana dashboard library
2. **Use variables** for namespace/service/instance filtering
3. **Group related metrics in rows** — logical organization
4. **Set default time range** — last 6 hours typically
5. **Add panel descriptions** — context for on-call engineers
6. **Configure units correctly** — bytes, percent, req/s, etc.
7. **Set meaningful color thresholds** — green/yellow/red
8. **Test with different time ranges** — ensure queries handle large windows
9. **Export as JSON** — version control all dashboards
10. **Use consistent colors** — same color = same meaning across dashboards
