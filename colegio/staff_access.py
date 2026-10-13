"""Server-side projections for employee banking privacy; no stored data changes."""

EMPLOYEE_PUBLIC_COLUMNS = ('id', 'name', 'document', 'position', 'position_id',
                           'phone', 'salary', 'status')
PAYROLL_SUMMARY_FIELDS = ('name', 'pay_date', 'rate', 'total_usd', 'total_ves')


def banking_allowed(user):
    return user.get('role') == 'admin'


def employee_columns(user):
    return '*' if banking_allowed(user) else ','.join(EMPLOYEE_PUBLIC_COLUMNS)


def payroll_columns(user):
    # Restricted profiles never receive the saved lines or their bank/holder data.
    return 'id,' + ','.join(f"json_extract(snapshot_json,'$.{key}') AS {key}"
                           for key in PAYROLL_SUMMARY_FIELDS)
