"""Draft-only entry point: never select the production Windows data directory."""
import os
from pathlib import Path


def isolate():
    base=os.environ.get('LOCALAPPDATA')
    if not base:raise RuntimeError('No se encuentra LOCALAPPDATA; no se abrirá ninguna base.')
    os.environ['LOCALAPPDATA']=str(Path(base)/'AulaRevisionIngresos')


if __name__=='__main__':
    isolate()
    from colegio import desktop
    desktop.TITLE='BORRADOR · '+desktop.TITLE
    desktop.main()
