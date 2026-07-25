# ADR 0004: Data-driven category attributes

Status: accepted

Category-specific fields are definitions stored in `category_attributes`, while listing values are stored as JSONB. This allows administrators to evolve cars, goods and services without schema migrations for every field.

The application validates values against definitions before moderation. Frequently searched attributes will later be projected into indexed columns or a search document; JSONB is not treated as the only search representation.

