"""Keep backups by a persisted publication sequence, independent of the PC clock."""
import json
from pathlib import Path

from .clock_guard import atomic_json


def retain_backups(directory, published, pattern, limit, *, created=True):
    directory, published = Path(directory), Path(published)
    history = directory/'.aula-backup-history.json'
    files = [p for p in directory.glob(pattern) if p.is_file()]
    try:
        data = json.loads(history.read_text(encoding='utf-8'))
        entries, counter = data['entries'], data['counter']
        if (data['version'] != 1 or not isinstance(entries, dict) or type(counter) is not int or counter < 0
                or any(type(v) is not int or not 0 < v <= counter for v in entries.values())):
            raise ValueError('Invalid backup inventory')
    except FileNotFoundError:
        entries, counter = {}, 0
    except (OSError, ValueError, KeyError, TypeError) as error:
        # An unreadable inventory must never authorize deleting a backup.
        raise OSError('No se pudo comprobar el orden de las copias; no se eliminaron respaldos.') from error
    # Existing copies without history can only be estimated once from file metadata.
    # Every newly published copy gets a greater sequence even after a clock rollback.
    for path in sorted(files, key=lambda p:(p.stat().st_mtime_ns, p.name)):
        if path.name not in entries:
            counter += 1
            entries[path.name] = counter
    if created:
        counter += 1
        entries[published.name] = counter
    atomic_json(history, {'version':1, 'counter':counter, 'entries':entries})
    ordered = sorted(files, key=lambda p:entries[p.name])
    for old in ordered[:-limit]:
        if old != published:
            old.unlink()
