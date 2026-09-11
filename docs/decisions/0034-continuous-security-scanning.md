# ADR 0034: CI blocks fixable high-impact security findings

Status: accepted

Lava runs a dedicated security workflow for pull requests, pushes to `main`, a
weekly schedule and manual dispatch. Dependency audit covers the deployed web
workspace and the API project. CodeQL analyzes JavaScript/TypeScript and Python
with the extended security query suite. Trivy scans committed files for secrets
and unsafe configuration, then scans the API, Web and Worker production images
for fixable HIGH and CRITICAL vulnerabilities.

Third-party GitHub Actions are pinned to full commit SHAs to reduce tag-mutation
risk. Scanner and audit-tool versions remain explicit so upgrades are reviewed.
The complete JavaScript graph currently fails only on CRITICAL advisories because
known HIGH findings are confined to the non-deployed Expo development toolchain;
the separately audited web production workspace fails at HIGH.

Production images install current operating-system security updates, run as
non-root users and omit development/test tooling. Runtime images also remove
unused Python or Web package managers, reducing both attack surface and transitive
advisories.
`ignore-unfixed` avoids blocking a release on findings for which the upstream OS
has no remediation, but no project-level vulnerability exceptions are added.
DAST and operational recovery drills remain separate pre-launch controls.
