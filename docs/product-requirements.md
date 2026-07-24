# Product requirements

## Vision

Lava is a Russian classifieds platform where organic reach is earned through relevance, completeness, trust and service quality—not payment.

## MVP users and scope

Guests browse and search. Individuals publish and communicate. Specialists maintain service profiles. Companies are modeled for later multi-user management. Moderators and administrators operate explicit audited workflows.

The MVP covers cars, goods and services; phone/password/VK authentication abstractions; profiles and verification; listings and media; search; favorites; chat; reviews; complaints; moderation; seller analytics; AI text/image assistance and credit accounting.

Delivery, marketplace payments, banking acquiring, native apps, Kubernetes and premature microservices are out of scope.

## Product invariants

- Paid placement never silently changes organic ranking.
- AI cannot invent characteristics, hide defects or falsify documents.
- AI-generated or materially transformed content is labeled.
- Every purchase states price, duration, units and renewal behavior before consent.
- Reviews require a platform-recorded interaction.

## First iteration acceptance

One documented command starts web, API, PostgreSQL, Redis, MinIO and worker. The web shows the three categories; API health responds; migrations and idempotent category seed run; automated checks exist.

