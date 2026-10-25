"""Atomic internal credit reservations in the existing POI database.

Integer credit subunits only. This ledger is NOT a provider balance and does not
claim a remote request is capped. Unknown charges remain reserved until reconciled.
No schema is changed until initialize() is called explicitly.
"""
import json
import re
import time

from .world_contract import ContractError


def _token(value):
    if not isinstance(value, str) or not re.fullmatch(r'[a-zA-Z0-9_.:-]{1,160}', value):
        raise ContractError('budget_identifier')
    return value


def _amount(value):
    if type(value) is not int or not 0 <= value <= 10**12:
        raise ContractError('budget_amount')
    return value


class CreditBudget:
    def __init__(self, repository):
        self.repo = repository

    def initialize(self):
        self.repo.initialize()
        with self.repo.transaction() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS world_credit_window (
                account TEXT NOT NULL, period TEXT NOT NULL, starts REAL NOT NULL,
                ends REAL NOT NULL, credit_limit INTEGER NOT NULL,
                PRIMARY KEY(account, period))''')
            c.execute('''CREATE TABLE IF NOT EXISTS world_credit_operation (
                account TEXT NOT NULL, operation TEXT NOT NULL, reserved INTEGER NOT NULL,
                charged INTEGER, state TEXT NOT NULL, periods TEXT NOT NULL,
                created REAL NOT NULL, PRIMARY KEY(account, operation))''')
            c.execute('''CREATE TABLE IF NOT EXISTS world_credit_entry (
                account TEXT NOT NULL, operation TEXT NOT NULL, period TEXT NOT NULL,
                amount INTEGER NOT NULL, PRIMARY KEY(account, operation, period),
                FOREIGN KEY(account, operation) REFERENCES world_credit_operation(account, operation),
                FOREIGN KEY(account, period) REFERENCES world_credit_window(account, period))''')
            c.execute('''CREATE TABLE IF NOT EXISTS world_credit_hold (
                account TEXT PRIMARY KEY, reason TEXT NOT NULL)''')
            c.execute('''CREATE TABLE IF NOT EXISTS world_credit_policy (
                account TEXT PRIMARY KEY, daily_limit INTEGER NOT NULL,
                rolling_limit INTEGER NOT NULL, configured REAL NOT NULL)''')
            c.execute('CREATE INDEX IF NOT EXISTS world_credit_operation_account_time ON world_credit_operation(account,created)')
            c.execute('''CREATE TABLE IF NOT EXISTS world_credit_scope (
                account TEXT NOT NULL, scope TEXT NOT NULL, starts REAL NOT NULL,
                ends REAL NOT NULL, credit_limit INTEGER NOT NULL,
                PRIMARY KEY(account,scope))''')
            c.execute('''CREATE TABLE IF NOT EXISTS world_credit_allocation (
                account TEXT NOT NULL, operation TEXT NOT NULL, scope TEXT NOT NULL,
                PRIMARY KEY(account,operation,scope),
                FOREIGN KEY(account,operation) REFERENCES world_credit_operation(account,operation),
                FOREIGN KEY(account,scope) REFERENCES world_credit_scope(account,scope))''')

    def configure_scope(self, account, scope, starts, ends, limit):
        """Explicit immutable pilot/layer cap; never resets existing spending."""
        import math
        _token(account); _token(scope); _amount(limit)
        if (any(type(v) not in (int, float) or not math.isfinite(v) for v in (starts, ends))
                or not 0 <= starts < ends or ends-starts > 86400 or limit == 0):
            raise ContractError('budget_scope_window')
        with self.repo.transaction() as c:
            old = c.execute('SELECT starts,ends,credit_limit FROM world_credit_scope WHERE account=? AND scope=?',
                            (account, scope)).fetchone()
            if old and tuple(old) != (starts, ends, limit):
                raise ContractError('budget_scope_immutable')
            c.execute('INSERT OR IGNORE INTO world_credit_scope VALUES (?,?,?,?,?)',
                      (account, scope, starts, ends, limit))

    @staticmethod
    def _scope_usage(c, account, scope):
        return c.execute('''SELECT COALESCE(SUM(COALESCE(o.charged,o.reserved)),0)
            FROM world_credit_allocation a JOIN world_credit_operation o USING(account,operation)
            WHERE a.account=? AND a.scope=?''', (account, scope)).fetchone()[0]

    def scope_status(self, account, scope):
        _token(account); _token(scope)
        c = self.repo.connect()
        try:
            row = c.execute('SELECT * FROM world_credit_scope WHERE account=? AND scope=?',
                            (account, scope)).fetchone()
            if not row:
                return None
            used = self._scope_usage(c, account, scope)
            return dict(row, committed=used, remaining=max(0, row['credit_limit']-used))
        finally:
            c.close()

    def configure_recurring(self, account, daily_limit, rolling_limit):
        """UTC days + trailing 31 days, independent of provider billing reset.

Includes previous pilot operations; never deletes or resets usage. An enabled
policy supersedes legacy fixed windows for NEW reservations only.
"""
        _token(account); _amount(daily_limit); _amount(rolling_limit)
        ceiling=93000 if account=='geoapify' else 30000
        if not 1 <= daily_limit <= rolling_limit <= ceiling:
            raise ContractError('budget_policy_invalid')
        with self.repo.transaction() as c:
            c.execute('''INSERT INTO world_credit_policy VALUES (?,?,?,?)
                ON CONFLICT(account) DO UPDATE SET daily_limit=excluded.daily_limit,
                rolling_limit=excluded.rolling_limit,configured=excluded.configured''',
                (account,daily_limit,rolling_limit,time.time()))

    @staticmethod
    def _recurring_status(c, account, now):
        # Rolling upgrades may still have the pre-rollout ledger schema.
        if not c.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='world_credit_policy'").fetchone():
            return []
        policy = c.execute('SELECT * FROM world_credit_policy WHERE account=?',(account,)).fetchone()
        if not policy:
            return []
        day = int(now // 86400) * 86400
        rows = []
        for period, start, end, limit in (
                ('utc_day',day,day+86400,policy['daily_limit']),
                ('rolling_31_days',now-31*86400,now,policy['rolling_limit'])):
            # Unresolved requests remain counted even across day/window changes.
            used = c.execute('''SELECT COALESCE(SUM(COALESCE(charged,reserved)),0)
                FROM world_credit_operation WHERE account=? AND
                (created>=? OR state IN ('reserved','uncertain'))''',(account,start)).fetchone()[0]
            rows.append(dict(period=period, starts=start, ends=end, credit_limit=limit,
                committed=used, remaining=max(0,limit-used),source='chaos_internal_ledger'))
        return rows

    def configure_window(self, account, period, starts, ends, limit):
        """Explicit windows from approved configuration; never reset usage in place."""
        import math
        _token(account); _token(period); _amount(limit)
        if period.startswith('carry:'):
            raise ContractError('carry_forward_reserved_period')
        if (any(type(v) not in (float, int) or not math.isfinite(v) for v in (starts, ends))
                or not 0 <= starts < ends):
            raise ContractError('budget_window')
        with self.repo.transaction() as c:
            old = c.execute('SELECT * FROM world_credit_window WHERE account=? AND period=?', (account, period)).fetchone()
            if old and (old['starts'] != starts or old['ends'] != ends):
                raise ContractError('budget_window_immutable')
            c.execute('''INSERT INTO world_credit_window VALUES (?,?,?,?,?)
                ON CONFLICT(account,period) DO UPDATE SET credit_limit=excluded.credit_limit''',
                (account, period, starts, ends, limit))

    def carry_forward(self, account, period, starts, ends, allowance):
        """One immutable window: retain every unresolved cost plus an explicit allowance.

        Does not settle operations, reset old entries or enable recurring spending.
        Existing period IDs cannot be reused, even when expired.
        """
        import math
        _token(account); _token(period); _amount(allowance)
        period = 'carry:' + period
        _token(period)
        if (not 0 < allowance <= 20 or
                any(type(v) not in (float, int) or not math.isfinite(v) for v in (starts, ends))
                or not starts <= time.time() < ends or ends-starts > 3600):
            raise ContractError('carry_forward_window_invalid')
        with self.repo.transaction() as c:
            if c.execute('SELECT 1 FROM world_credit_window WHERE account=? AND period=?',
                         (account, period)).fetchone():
                raise ContractError('carry_forward_already_exists')
            if c.execute('SELECT 1 FROM world_credit_policy WHERE account=?', (account,)).fetchone():
                raise ContractError('carry_forward_recurring_policy_exists')
            if c.execute('SELECT 1 FROM world_credit_hold WHERE account=?', (account,)).fetchone():
                raise ContractError('budget_account_held')
            if c.execute('SELECT 1 FROM world_credit_window WHERE account=? AND starts<=? AND ends>?',
                         (account, starts, starts)).fetchone():
                raise ContractError('carry_forward_active_window_exists')
            old = c.execute("SELECT operation,coalesce(charged,reserved) amount FROM world_credit_operation "
                            "WHERE account=? AND state IN ('reserved','uncertain')", (account,)).fetchall()
            carried = sum(row['amount'] for row in old)
            c.execute('INSERT INTO world_credit_window VALUES (?,?,?,?,?)',
                      (account, period, starts, ends, carried+allowance))
            c.executemany('INSERT INTO world_credit_entry VALUES (?,?,?,?)',
                          [(account, row['operation'], period, row['amount']) for row in old])
        return dict(carried=carried, allowance=allowance, credit_limit=carried+allowance,
                    unresolved_operations=len(old), period=period)

    def reserve(self, account, operation, upper_bound, *, now=None, scopes=()):
        _token(account); _token(operation); _amount(upper_bound)
        if not isinstance(scopes, tuple) or len(scopes) > 2 or len(set(scopes)) != len(scopes):
            raise ContractError('budget_scopes')
        for scope in scopes:
            _token(scope)
        if upper_bound == 0:
            raise ContractError('budget_cost_unproven')
        now = time.time() if now is None else now
        with self.repo.transaction() as c:
            old = c.execute('SELECT * FROM world_credit_operation WHERE account=? AND operation=?',
                            (account, operation)).fetchone()
            if old:
                if old['reserved'] != upper_bound:
                    raise ContractError('budget_operation_conflict')
                # A duplicate cannot send again, even after successful settlement.
                return False
            if c.execute('SELECT 1 FROM world_credit_hold WHERE account=?', (account,)).fetchone():
                raise ContractError('budget_account_held')
            for scope in scopes:
                window = c.execute('SELECT * FROM world_credit_scope WHERE account=? AND scope=?',
                                   (account, scope)).fetchone()
                if not window or not window['starts'] <= now < window['ends']:
                    raise ContractError('budget_scope_inactive')
                if self._scope_usage(c, account, scope) + upper_bound > window['credit_limit']:
                    raise ContractError('budget_scope_exhausted')
            recurring = self._recurring_status(c, account, now)
            if recurring:
                if any(w['committed'] + upper_bound > w['credit_limit'] for w in recurring):
                    raise ContractError('budget_exhausted')
                c.execute('INSERT INTO world_credit_operation VALUES (?,?,?,?,?,?,?)',
                    (account,operation,upper_bound,None,'reserved','[]',now))
                if scopes:
                    c.executemany('INSERT INTO world_credit_allocation VALUES (?,?,?)',
                                  [(account, operation, s) for s in scopes])
                return True
            # Unresolved in-flight requests across a reset must not become free.
            if c.execute('''SELECT 1 FROM world_credit_entry e
                JOIN world_credit_operation o USING(account, operation)
                JOIN world_credit_window w USING(account, period)
                WHERE e.account=? AND o.state IN ('reserved','uncertain') AND w.ends<=?
                AND NOT EXISTS (
                    SELECT 1 FROM world_credit_entry carried
                    JOIN world_credit_window active USING(account,period)
                    WHERE carried.account=o.account AND carried.operation=o.operation
                      AND active.starts<=? AND active.ends>?
                      AND active.period LIKE 'carry:%'
                      AND carried.amount>=coalesce(o.charged,o.reserved)) LIMIT 1''',
                         (account, now, now, now)).fetchone():
                raise ContractError('budget_previous_period_unresolved')
            windows = c.execute('SELECT * FROM world_credit_window WHERE account=? AND starts<=? AND ends>?',
                                (account, now, now)).fetchall()
            if not windows:
                raise ContractError('budget_unconfigured')
            for w in windows:
                used = c.execute('SELECT COALESCE(SUM(amount),0) FROM world_credit_entry WHERE account=? AND period=?',
                                 (account, w['period'])).fetchone()[0]
                if used + upper_bound > w['credit_limit']:
                    raise ContractError('budget_exhausted')
            periods = sorted(w['period'] for w in windows)
            c.execute('INSERT INTO world_credit_operation VALUES (?,?,?,?,?,?,?)',
                      (account, operation, upper_bound, None, 'reserved', json.dumps(periods), now))
            c.executemany('INSERT INTO world_credit_entry VALUES (?,?,?,?)',
                          [(account, operation, p, upper_bound) for p in periods])
            if scopes:
                c.executemany('INSERT INTO world_credit_allocation VALUES (?,?,?)',
                              [(account, operation, s) for s in scopes])
            return True

    def settle(self, account, operation, charged=None):
        """Only observed charges or a proven unsent request (0) release credits."""
        _token(account); _token(operation)
        if charged is not None:
            _amount(charged)
        with self.repo.transaction() as c:
            old = c.execute('SELECT * FROM world_credit_operation WHERE account=? AND operation=?',
                            (account, operation)).fetchone()
            if not old:
                raise ContractError('budget_operation_missing')
            if old['state'] == 'settled':
                if old['charged'] != charged:
                    raise ContractError('budget_settlement_conflict')
                return
            if charged is None:
                c.execute("UPDATE world_credit_operation SET state='uncertain' WHERE account=? AND operation=?",
                          (account, operation))
                return
            c.execute("UPDATE world_credit_operation SET state='settled', charged=? WHERE account=? AND operation=?",
                      (charged, account, operation))
            c.execute('UPDATE world_credit_entry SET amount=? WHERE account=? AND operation=?',
                      (charged, account, operation))
            if charged > old['reserved']:
                # Record reality, never clamp it to an incorrect estimate.
                c.execute('INSERT OR REPLACE INTO world_credit_hold VALUES (?,?)',
                          (account, 'observed_charge_exceeded_reservation'))

    def estimate_geoapify(self,operation):
        """Keep all six reserved units for a validated <=100 result page; no reported charge claim."""
        with self.repo.transaction() as c:
            row=c.execute("SELECT reserved,state FROM world_credit_operation WHERE account='geoapify' AND operation=?",(operation,)).fetchone()
            if not row or row['reserved']!=6 or row['state']!='uncertain':
                raise ContractError('geoapify_estimate_not_eligible')
            c.execute("UPDATE world_credit_operation SET state='estimated' WHERE account='geoapify' AND operation=?",(operation,))

    def status(self, account, *, now=None):
        _token(account)
        now = time.time() if now is None else now
        c = self.repo.connect()
        try:
            recurring = self._recurring_status(c, account, now)
            if recurring:
                return recurring
            rows = c.execute('''SELECT w.period, w.credit_limit, w.starts, w.ends,
                COALESCE(SUM(e.amount),0) AS committed FROM world_credit_window w
                LEFT JOIN world_credit_entry e USING(account,period)
                WHERE w.account=? AND w.starts<=? AND w.ends>?
                GROUP BY w.account,w.period ORDER BY w.period''', (account, now, now)).fetchall()
            return [dict(r, remaining=max(0, r['credit_limit']-r['committed']),
                         source='chaos_internal_ledger') for r in rows]
        finally:
            c.close()
