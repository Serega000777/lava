# ADR 0001: Modular monolith

Status: accepted

Lava will use a domain-oriented modular monolith. It keeps transactions and operations simple during product discovery while preserving clear module boundaries that can later become services. Independent web, API and worker processes are not separate business microservices.

