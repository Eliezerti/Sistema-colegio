"""Independent permission contract and generated evidence, not inferred role policy."""
import ast
import csv
import json
import os
from pathlib import Path

ALL = ('admin', 'cashier', 'reader')
ADMIN = ('admin',)
WRITERS = ('admin', 'cashier')

GET_ALL = ('session', 'session-status', 'clock-status', 'rate-gate', 'state', 'cash-preview',
           'backup-status', 'bank-book','income-book', 'daily-report', 'daily-report.pdf', 'monthly-report','monthly-report.pdf','monthly-report.csv', 'health', 'export')
GET_ADMIN = ('audit', 'audit.csv', 'audit.pdf', 'import-template', 'import-guide',
             'backup', 'maintenance-review')
POST_ADMIN = ('bank-profile','bank-preview','bank-import','bank-link','bank-auto','bank-unlink','bank-classify','bank-unclassify','income-account','income-category','income-assign','income-other','income-void-other','income-void-deposit','settings', 'backup-directory', 'grades', 'guardians', 'students',
              'users', 'password', 'void-payment', 'void-expense', 'cancel-charge',
                'import-roster', 'reopen-cash', 'transition-year',
              'cancel-plan', 'correct-billing-start', 'archive-student', 'archive-guardian',
              'restore-student', 'restore-guardian', 'delete-grade',
               'delete-unused-record', 'clock-confirm', 'session-preferences',
              'recovery-notice-ack', 'crypto-prepare', 'crypto-confirm', 'crypto-unlock',
              'probe-backup', 'export-encrypted-backup', 'backup-now', 'backup-cloud-declare', )
POST_WRITERS = ('income-deposit','generate', 'payments', 'collections', 'rates', 'expenses', 'charges', 'close-cash',
                'guardian-documents', 'payment-plans')


def cases():
    result = []
    def add(method, route, roles, success, key=None, body=None):
        result.append(dict(method=method, route=route, roles=roles, success=success,
                           key=key or route.split('?')[0], body=body or {}))
    for route in GET_ALL: add('GET', route, (*ALL, 'anonymous') if route=='session' else ALL, 200)
    for route in GET_ADMIN: add('GET', route, ADMIN, 200)
    add('GET', 'year-roster?year=2020', ADMIN, 200)
    for kind in ('students', 'guardians'):
        for extension in ('', '.pdf'):
            add('GET', 'directory/'+kind+extension, ALL, 200, 'directory/')
    for kind in ('enrollment', 'receipt', 'payment-plan', 'year-transition', 'guardian-document', 'cash-close'):
        for extension in ('', '.pdf'):
            add('GET', kind+'/0'+extension, ALL, 400, kind+'/')
    add('GET', 'guardian-account/0', ALL, 400, 'guardian-account/')
    add('GET', 'archive-preview/student/0', ADMIN, 400, 'archive-preview/')
    for kind in ('students', 'payments', 'expenses'):
        add('GET', 'export?type='+kind, ALL, 200, 'export')
    for route in POST_ADMIN:
        add('POST', route, ADMIN, 200 if route in ('backup-now','crypto-unlock','bank-auto') else 400,
            body={'password':'FICTICIO-respaldo-seguro-2026'} if route=='crypto-unlock' else None)
    for route in POST_WRITERS: add('POST', route, WRITERS, 400)
    add('POST', 'confirm-rate', ALL, 400)
    add('POST', 'session-activity', ALL, 200)
    add('POST', 'logout', ALL, 200)
    # These endpoints have mode/setup/data validation before session authentication.
    for route in ('setup', 'login'): add('POST', route, (*ALL, 'anonymous'), 400)
    for route in ('demo-login', 'demo-presence'): add('POST', route, (*ALL, 'anonymous'), 403)
    add('POST', 'demo-exit', ALL, 403)
    return result


def endpoint_inventory():
    """Discover comparisons/prefixes and imported action sets; new routes require a case."""
    from colegio.server import DIRECTORY_ACTIONS, ARCHIVE_ACTIONS
    source = Path(__file__).resolve().parents[1]/'colegio/server.py'
    from colegio.income_book import ACTIONS as INCOME_ACTIONS
    from colegio.bank_book import ACTIONS as BANK_ACTIONS
    discovered = set(BANK_ACTIONS) | set(DIRECTORY_ACTIONS) | set(ARCHIVE_ACTIONS) | set(INCOME_ACTIONS)
    tree = ast.parse(source.read_text(encoding='utf-8'))
    # Tombstones have their own HTTP/profile/nonmutation contract in test_staff_retirement.
    tree.body = [node for node in tree.body if not isinstance(node, ast.FunctionDef) or node.name != 'retired_route']
    def strings(node):
        if isinstance(node, ast.Constant) and isinstance(node.value, str): return {node.value}
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            return set().union(*(strings(n) for n in node.elts))
        return set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Compare) and isinstance(node.left, ast.Name) and node.left.id=='endpoint':
            for right in node.comparators: discovered.update(strings(right))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
            if node.func.value.id=='endpoint' and node.func.attr=='startswith':
                for argument in node.args: discovered.update(strings(argument))
    return discovered


def write_report(records, inventory):
    directory = os.environ.get('AULA_PERMISSION_REPORT_DIR')
    if not directory: return
    root = Path(directory); root.mkdir(parents=True, exist_ok=True)
    (root/'permisos.json').write_text(json.dumps({'endpoints': sorted(inventory), 'cases': records},
                                                indent=2, ensure_ascii=False), encoding='utf-8')
    with (root/'permisos.csv').open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=('method','route','role','csrf','expected','actual'))
        writer.writeheader(); writer.writerows(records)
    lines = ['# Matriz de permisos comprobada · B1', '',
             '400 indica que el perfil alcanzó la validación de una solicitud ficticia inválida; '+
             'no se presenta como operación completada. Los permisos se comparan con un contrato independiente.', '',
             '| Método | Ruta | Perfil | CSRF | Esperado | Real |', '|---|---|---|---|---|---|']
    lines.extend('| '+' | '.join(str(r[k]) for k in ('method','route','role','csrf','expected','actual'))+' |' for r in records)
    (root/'permisos.md').write_text('\n'.join(lines)+'\n', encoding='utf-8')
