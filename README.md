# File Friend models

Standard-library-only shared contracts: `FileReference`, `UploadRequest`, `FriendConfig`, `validate_id` and `validate_metadata`. Python 3.13+.

```python
from byteforge_mcp_file_friend_models import FileReference, UploadRequest
```

## Local development

The virtual environment lives at this repository root. Create it before writing `.gitignore`; recreating it can overwrite that file with `*`.

```bash
source bin/activate
uv pip install --require-hashes -r dev-requirements.txt -r build-requirements.txt
uv build --wheel --no-build-isolation
uv pip install --no-deps dist/byteforge_mcp_file_friend_models-0.0.1-py3-none-any.whl
python -m pytest
ruff check src tests
```

Tests exercise the installed wheel, without a source-path override. The pytest configuration excludes the parent workspace's PostgreSQL fixture. Neither the models nor their tests require Flask, PostgreSQL or core.

Dependency locks retain the versions and hashes already validated in the workspace. To refresh, use `uv pip compile dev-requirements.in --generate-hashes --python-version 3.13 --exclude-newer '7 days' -o dev-requirements.txt`, and the equivalent command for build requirements. Review version changes before installing.

## Extraction status

This independent repository contains an unchanged copy of the original models implementation. The old `src/ff/models` module remains in the parent workspace until its consumers are migrated. Do not make divergent model changes during that transition.

Licensed under the MIT License; see `LICENSE`. The approved public repository is `jmazzahacks/byteforge-mcp-file-friend-models`.
