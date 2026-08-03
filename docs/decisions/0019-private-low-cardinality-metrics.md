# 0019: Private low-cardinality metrics

## Decision

Expose a hidden, bearer-protected OpenMetrics endpoint. It uses an in-process HTTP
counter/duration accumulator and durable queue aggregates. HTTP labels are limited
to method, registered route template and status. The endpoint is disabled without
a strong deployment secret and returns `404` for every unauthorized request.

## Consequences

MVP deployments can scrape useful health and saturation signals without adding a
metrics vendor or exposing business data. Counters are process-local and reset on
restart; horizontally scaled deployments must aggregate all API instances. Alert
routing, long-term retention and dashboards stay deployment concerns.
