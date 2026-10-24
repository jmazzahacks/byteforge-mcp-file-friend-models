from dataclasses import replace
from pathlib import Path

import pytest

from byteforge_mcp_file_friend_models import (
    FileReference,
    FriendConfig,
    UploadRequest,
    validate_id,
    validate_metadata,
)


def test_request_normalizes_digest_and_preserves_contract() -> None:
    request = UploadRequest.from_dict({'filename': 'report.pdf', 'sha256': 'AB' * 32, 'size': 0})
    assert request.to_dict() == {
        'filename': 'report.pdf', 'sha256': 'ab' * 32, 'size': 0, 'ttl': 86400,
    }


@pytest.mark.parametrize('metadata', [
    {'filename': '../escape'}, {'filename': 'dir\\escape'}, {'filename': 'bad\nname'},
    {'sha256': 'wrong'}, {'ttl': '0'}, {'ttl': '604801'}, {'ttl': '1.5'},
    {'filename': 'é' * 101}, {'ttl': True},
])
def test_invalid_metadata_rejected(metadata: dict) -> None:
    values = {'filename': 'report.pdf', 'sha256': 'ab' * 32, **metadata}
    with pytest.raises(ValueError):
        validate_metadata(values, 3)


@pytest.mark.parametrize('size', [-1, True, 1.5])
def test_invalid_size_rejected(size: object) -> None:
    with pytest.raises(ValueError):
        validate_metadata({'filename': 'report.pdf', 'sha256': 'ab' * 32}, size)


@pytest.mark.parametrize('file_id', ['a' * 31, 'A' * 32, '../escape', None])
def test_invalid_capability_rejected(file_id: object) -> None:
    with pytest.raises(ValueError):
        validate_id(file_id)


def test_reference_roundtrip() -> None:
    reference = FileReference('a' * 32, 'https://ff.example/file', 'report.pdf', 'ab' * 32, 3, 100, 200)
    assert FileReference.from_dict(reference.to_dict()) == reference


@pytest.mark.parametrize('overrides', [
    {'expires_at': 99}, {'created_at': True}, {'url': 'file:///tmp/report.pdf'}, {'id': 'invalid'},
])
def test_reference_rejects_invalid_contract(overrides: dict) -> None:
    values = FileReference('a' * 32, 'https://ff.example/file', 'report.pdf', 'ab' * 32, 3, 100, 200).to_dict()
    with pytest.raises(ValueError):
        FileReference.from_dict({**values, **overrides})


@pytest.mark.parametrize('url', [
    'https://ff.example/prefix', 'https://ff.example:0',
    'https://ff.example:abc', 'https://ff.example\n',
])
def test_public_url_rejects_paths_and_invalid_ports(tmp_path: Path, url: str) -> None:
    with pytest.raises(ValueError):
        FriendConfig(tmp_path, url, hook_token='hook').validate()


def test_configuration_requires_hook_and_finite_deadlines(tmp_path: Path) -> None:
    config = FriendConfig(tmp_path, 'https://ff.example', hook_token='hook')
    config.validate()
    for invalid in (replace(config, hook_token=''), replace(config, worker_timeout=float('nan'))):
        with pytest.raises(ValueError):
            invalid.validate()
