# Observability

`GET /internal/metrics` exports OpenMetrics-compatible technical metrics for HTTP
traffic, queue depth, oldest pending task and worker health. HTTP labels use route
templates such as `/listings/{listing_id}` rather than concrete URLs, preventing
UUID leakage and unbounded label cardinality. Metrics contain no phones, profile
fields, message bodies, search queries or task payloads.

The endpoint is disabled and responds with `404` unless `METRICS_TOKEN` contains
at least 32 characters. Scrapers send it as `Authorization: Bearer <token>`.
Missing and incorrect tokens also receive `404`; comparison is constant-time.
Store and rotate this token through the deployment secrets manager, never in Git.

The exporter reports a missing Redis heartbeat as `lava_worker_healthy 0`. A
database failure returns an unsuccessful scrape so monitoring can alert on the
exporter or database target. Alert routing and retention belong to the deployment
monitoring system and require environment-specific configuration.
