"""Isolated, read-only access probe (parent process imposes a timeout)."""
import json
import os
import stat
import sys


def probe(location):
    try:
        info = os.stat(location)
        if stat.S_ISREG(info.st_mode):
            with open(location, 'rb') as stream:
                stream.read(1)
            return {'state': 'accessible', 'detail': 'Fichier présent et lisible', 'kind': 'file', 'bytes': info.st_size}
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(location) as items:
                next(items, None)
            return {'state': 'accessible', 'detail': 'Dossier présent et consultable', 'kind': 'folder'}
        return {'state': 'unsupported', 'detail': 'Emplacement qui n’est ni un fichier ni un dossier ordinaire'}
    except FileNotFoundError:
        return {'state': 'missing', 'detail': 'Emplacement introuvable depuis cet ordinateur'}
    except PermissionError:
        return {'state': 'denied', 'detail': 'Accès refusé depuis cet ordinateur'}
    except OSError:
        return {'state': 'unavailable', 'detail': 'Emplacement inaccessible depuis cet ordinateur'}


if __name__ == '__main__':
    print(json.dumps(probe(json.load(sys.stdin)['location']), ensure_ascii=False))
