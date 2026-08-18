# ADR 0025: Private normalized message media

Status: accepted

## Decision

The MVP accepts JPEG, PNG and WebP message images up to 5 MiB and three files per
message. Lava decodes by file signature, enforces pixel limits, applies EXIF
orientation, removes metadata and stores a newly encoded WebP object. Original
bytes and filenames are never retained.

Only the message sender may upload. Both conversation participants may list and
download media through authenticated endpoints; moderators may download evidence
only with `moderation:read`. Objects and responses use `private, no-store` and no
public URL is issued.

Message-row locks serialize uploads with report creation. Once a message is
reported, its attachment set is immutable. A user block prevents new uploads.

## Consequences

Images cannot bypass contact blocks or mutate reported evidence. A text message
commits before its optional upload, so storage failure never loses text and the UI
must report partial success. Malware-bearing general files, video and documents
remain unsupported.
