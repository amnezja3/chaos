import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OPERATOR_PROFILE_WRITER_FILES = (
    Path("tools/ghostnetwork_runtime.py"),
    Path("scripts/reset_user_password.py"),
    Path("tools/admin_reset_test_state.py"),
)

# These are explicit offline migration/recovery utilities. Runtime code must use
# UserStore's guarded profile API.  The allowlist is deliberately per function,
# so adding unrelated raw profile SQL to one of these files still fails review.
DIRECT_PROFILE_SQL_ALLOWLIST = {
    Path("tools/migrate_app_contracts.py"): {"migrate_user_apps"},
    Path("tools/prepare_example_db.py"): {"prepare_example_db"},
    Path("tools/profile_store_migration.py"): {"rollback_user"},
    # Sprint 130.11 is the only exact-account operator recovery exception.
    # These writes are plan/checksum/CAS gated and are never imported by runtime.
    Path("tools/repair_trollu2_profile.py"): {
        "apply_level_step", "final_settlement", "rollback_recovery",
    },
    Path("tools/repair_trollu2_identity.py"): {"apply_identity"},
    Path("scripts/app_catalog_cleanup.py"): {"write_user_profile"},
    Path("scripts/db_migrations/migration_helpers.py"): {"write_profile"},
}


def python_sources():
    for directory in (ROOT, ROOT / "tools", ROOT / "scripts"):
        pattern = "*.py" if directory == ROOT else "**/*.py"
        for path in directory.glob(pattern):
            if "tests" in path.parts or "__pycache__" in path.parts:
                continue
            yield path


def legacy_save_calls(relative_path):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(relative_path))
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        function = node.func
        if isinstance(function, ast.Attribute) and function.attr == "save_profile":
            findings.append(f"{relative_path.as_posix()}:{node.lineno}")
    return findings


def named_method_calls(relative_path, method_name):
    source = (ROOT / relative_path).read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(relative_path))
    return [
        f"{relative_path.as_posix()}:{node.lineno}"
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == method_name
    ]


def direct_profile_sql(path):
    relative = path.relative_to(ROOT)
    if relative == Path("database.py"):
        return []

    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(relative))
    findings = []

    class ProfileSqlVisitor(ast.NodeVisitor):
        def __init__(self):
            self.functions = []

        def visit_FunctionDef(self, node):
            self.functions.append(node.name)
            self.generic_visit(node)
            self.functions.pop()

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Constant(self, node):
            if not isinstance(node.value, str):
                return
            sql = " ".join(node.value.lower().split())
            writes_user_profile = (
                "profile_json" in sql
                and any(
                    statement in sql
                    for statement in (
                        "update users",
                        "insert into users",
                        "replace into users",
                    )
                )
            )
            if not writes_user_profile:
                return
            function_name = self.functions[-1] if self.functions else "<module>"
            allowed_functions = DIRECT_PROFILE_SQL_ALLOWLIST.get(relative, set())
            if function_name not in allowed_functions:
                findings.append(
                    f"{relative.as_posix()}:{node.lineno}:{function_name}"
                )

    ProfileSqlVisitor().visit(tree)
    return findings


class ProfileWriterStaticContractTests(unittest.TestCase):
    def test_non_database_sources_have_no_legacy_save_profile_calls(self):
        findings = []
        for path in python_sources():
            relative = path.relative_to(ROOT)
            if relative == Path("database.py"):
                continue
            findings.extend(legacy_save_calls(relative))
        self.assertEqual([], findings)

    def test_runtime_has_no_direct_users_profile_json_sql(self):
        findings = []
        for path in python_sources():
            findings.extend(direct_profile_sql(path))
        self.assertEqual([], findings)

    def test_production_sources_do_not_call_disabled_set_balance(self):
        findings = []
        for path in python_sources():
            relative = path.relative_to(ROOT)
            if relative == Path("database.py"):
                continue
            findings.extend(named_method_calls(relative, "set_balance"))
        self.assertEqual([], findings)

    def test_operator_profile_tools_use_guarded_writer_boundary(self):
        for relative in OPERATOR_PROFILE_WRITER_FILES:
            self.assertEqual([], legacy_save_calls(relative), relative.as_posix())
            self.assertEqual([], direct_profile_sql(ROOT / relative), relative.as_posix())
            guarded = (
                named_method_calls(relative, "save_profile_guarded")
                + named_method_calls(relative, "patch_profile_guarded")
            )
            self.assertTrue(guarded, relative.as_posix())

    def test_ordinary_profile_overlay_does_not_seed_inventory(self):
        source = (ROOT / "run.py").read_text(encoding="utf-8")
        tree = ast.parse(source, filename="run.py")
        overlay = next(
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "apply_runtime_stores_to_profile"
        )
        inventory_writes = []
        for node in ast.walk(overlay):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr in {"seed_from_profile", "write_from_profile"}:
                receiver = ast.unparse(node.func.value)
                if "inventory" in receiver:
                    inventory_writes.append(f"{receiver}.{node.func.attr}:{node.lineno}")
        self.assertEqual([], inventory_writes)


if __name__ == "__main__":
    unittest.main()
