# How To Build and Publish

This guide shows the recommended flow to build and publish `tseda` with `uv`, including how to recover from the common "file already exists" error.

## Prerequisites

- You are in the project root.
- Your virtual environment is active.
- You have publish credentials configured for your package index.

## Version Bump Commands (uv)

Use `uv version` to update the project version in `pyproject.toml`.

- Bump **minor** version (e.g., `2.2.0 -> 2.3.0`):

```bash
uv version --bump minor
```

- Bump **major** version (e.g., `2.2.0 -> 3.0.0`):

```bash
uv version --bump major
```

Optional preview without writing changes:

```bash
uv version --bump minor --dry-run
```

## Standard Build and Publish Flow

1. Clean previous build artifacts:

```bash
rm -rf dist build src/tseda.egg-info
```

2. Build source and wheel distributions:

```bash
uv build
```

3. Publish:

```bash
uv publish
```

## If Publish Fails With "File Already Exists"

This usually means a package with the same version has already been uploaded.
Deleting local files alone will not fix that server-side conflict.

Use this flow:

1. Bump the version in `pyproject.toml`.
2. Clean local build artifacts:

```bash
rm -rf dist build src/tseda.egg-info
```

3. Rebuild:

```bash
uv build
```

4. Publish again:

```bash
uv publish
```

## Quick Troubleshooting

- Build fails due to stale local files:
  - Run `rm -rf dist build src/tseda.egg-info`, then `uv build`.
- Publish fails because artifact already exists remotely:
  - Increase version in `pyproject.toml`, rebuild, republish.

## Optional Verification

After build, verify that expected files exist in `dist/`:

```bash
ls -lh dist
```
