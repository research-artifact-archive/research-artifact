"""Read one distributed source without extracting or modifying the artifact."""
from hashlib import sha256
import io
import json
from pathlib import Path
import tarfile


def checked_bytes(root, record):
    path = (root / record['path']).resolve()
    if not path.is_relative_to(root):
        raise ValueError('Source path escapes the artifact')
    data = path.read_bytes()
    check_record(data, record)
    return data


def check_record(data, record):
    if len(data) != record['bytes'] or sha256(data).hexdigest() != record['sha256']:
        raise ValueError('Distributed source differs from its layout record: ' + record['path'])


def read_source(root, workspace_path):
    root = Path(root).resolve()
    layout = json.loads((root / 'reproduce/layout.json').read_text())
    direct = [(record, None) for record in layout['files']
              if record['workspace'] == workspace_path]
    archived = [(record, archive) for archive in layout['archives']
                for record in archive['files'] if record['workspace'] == workspace_path]
    matches = direct + archived
    if len(matches) != 1:
        raise ValueError('Expected one distributed source: ' + workspace_path)
    record, archive = matches[0]
    if archive is None:
        return checked_bytes(root, record)
    # Verify the lossless parts, then stream to just the requested member.
    # No archive path is ever written to disk.
    joined = io.BytesIO(b''.join(checked_bytes(root, part) for part in archive['parts']))
    with tarfile.open(fileobj=joined, mode='r|gz') as stream:
        for member in stream:
            if member.name != record['workspace']:
                continue
            if not member.isfile() or member.size != record['bytes']:
                raise ValueError('Unexpected archived member type or size')
            content = stream.extractfile(member)
            if content is None:
                raise ValueError('Cannot read archived source')
            data = content.read()
            check_record(data, record)
            return data
    raise ValueError('Source is absent from its archive: ' + record['path'])
