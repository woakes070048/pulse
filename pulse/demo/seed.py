# Copyright (c) 2026, Tridz and contributors
# License: MIT
"""
Pulse demo data seeder.

Entry points
------------
    seed_demo_data()   — create all demo records (idempotent, skips existing)
    clear_demo_data()  — remove every record created by this seeder

Bench
-----
    bench --site <site> pulse-load-demo
    bench --site <site> pulse-clear-demo
    bench --site <site> execute pulse.demo.seed.seed_demo_data
    bench --site <site> execute pulse.demo.seed.clear_demo_data
"""

import random
from datetime import date

import frappe
from frappe.utils import add_days, getdate, now

from pulse.demo.data import (
    ASSIGNMENTS,
    COMPLETION_RATE,
    DEPARTMENTS,
    EMPLOYEE_BRANCH,
    EMPLOYEE_DEPARTMENT,
    END_DATE,
    HIERARCHY,
    SOP_TEMPLATES,
    START_DATE,
    USERS,
)


# ── Public API ─────────────────────────────────────────────────────────────────

def seed_demo_data() -> None:
    """Create all Pulse demo records. Safe to re-run — skips existing data."""
    if frappe.db.count("Pulse Employee") > 0:
        frappe.msgprint(
            "Demo data already present. Run clear_demo_data() first if you want a fresh seed."
        )
        return

    random.seed(42)
    frappe.set_user("Administrator")

    _ensure_pulse_roles()
    _create_users()
    _create_departments()
    _create_employees()
    _create_templates()
    _create_assignments()
    _create_runs()
    _create_score_snapshots()
    _create_corrective_actions()

    frappe.db.commit()
    frappe.msgprint(
        f"Demo data seeded: {len(USERS)} users · {len(DEPARTMENTS)} departments · "
        f"{len(SOP_TEMPLATES)} SOP templates · runs from {START_DATE} to {END_DATE}."
    )


def clear_demo_data() -> None:
    """Remove all records created by this seeder."""
    frappe.set_user("Administrator")

    for doctype in [
        "Corrective Action",
        "Score Snapshot",
        "SOP Run",
        "SOP Assignment",
        "SOP Template",
        "Pulse Employee",
        "Pulse Department",
    ]:
        for name in frappe.get_all(doctype, pluck="name"):
            frappe.delete_doc(doctype, name, force=1, ignore_permissions=True)

    for email, _, _ in USERS:
        if frappe.db.exists("User", email):
            frappe.delete_doc("User", email, force=1, ignore_permissions=True)

    frappe.db.commit()
    frappe.msgprint("Demo data cleared.")


# ── Internal helpers ───────────────────────────────────────────────────────────

def _ensure_pulse_roles() -> None:
    from pulse.install import create_default_pulse_role_records
    create_default_pulse_role_records()


def _create_users() -> None:
    _ROLE_MAP = {
        "Operator":     "Pulse User",
        "Supervisor":   "Pulse Manager",
        "Area Manager": "Pulse Leader",
        "Executive":    "Pulse Executive",
    }
    for email, full_name, pulse_role in USERS:
        sys_role = _ROLE_MAP.get(pulse_role, "Pulse User")
        if frappe.db.exists("User", email):
            frappe.get_doc("User", email).add_roles(sys_role, "System Manager")
            continue

        parts = full_name.split()
        user = frappe.get_doc({
            "doctype":          "User",
            "email":            email,
            "first_name":       parts[0],
            "last_name":        parts[-1] if len(parts) > 1 else "",
            "enabled":          1,
            "user_type":        "System User",
            "send_welcome_email": 0,
        })
        user.new_password = "Demo@123"
        user.insert(ignore_permissions=True)
        user.add_roles(sys_role, "System Manager")

    frappe.db.commit()


def _create_departments() -> None:
    for dept_name, description in DEPARTMENTS:
        if frappe.db.exists("Pulse Department", dept_name):
            continue
        frappe.get_doc({
            "doctype":         "Pulse Department",
            "department_name": dept_name,
            "description":     description,
            "is_active":       1,
        }).insert(ignore_permissions=True)

    frappe.db.commit()


def _create_employees() -> None:
    name_to_emp: dict[str, str] = {}

    for full_name, reports_to_name in HIERARCHY:
        email      = next(e for e, n, _ in USERS if n == full_name)
        dept       = EMPLOYEE_DEPARTMENT.get(full_name, "Operations")
        branch     = EMPLOYEE_BRANCH.get(full_name, "")
        pulse_role = next(r for e, n, r in USERS if n == full_name)
        reports_to = name_to_emp.get(reports_to_name) if reports_to_name else None

        emp = frappe.get_doc({
            "doctype":       "Pulse Employee",
            "employee_name": full_name,
            "user":          email,
            "pulse_role":    pulse_role,
            "branch":        branch,
            "department":    dept,
            "reports_to":    reports_to,
            "is_active":     1,
        })
        emp.insert(ignore_permissions=True)
        name_to_emp[full_name] = emp.name

    frappe.db.commit()


def _create_templates() -> None:
    active_from = START_DATE.isoformat()

    for title, dept, freq, owner_role, items in SOP_TEMPLATES:
        if frappe.db.exists("SOP Template", {"title": title}):
            continue

        checklist = [
            {
                "description":      desc,
                "sequence":         seq,
                "weight":           weight,
                "item_type":        itype,
                "evidence_required": evidence,
            }
            for desc, seq, weight, itype, evidence in items
        ]
        frappe.get_doc({
            "doctype":       "SOP Template",
            "title":         title,
            "department":    dept,
            "frequency_type": freq,
            "owner_role":    owner_role,
            "active_from":   active_from,
            "is_active":     1,
            "checklist_items": checklist,
        }).insert(ignore_permissions=True)

    frappe.db.commit()


def _create_assignments() -> None:
    for email, template_title in ASSIGNMENTS:
        templates = frappe.get_all("SOP Template", filters={"title": template_title}, limit=1)
        emps      = frappe.get_all("Pulse Employee", filters={"user": email}, limit=1)
        if not templates or not emps:
            continue
        if frappe.db.exists("SOP Assignment", {"template": templates[0].name, "employee": emps[0].name}):
            continue
        frappe.get_doc({
            "doctype":   "SOP Assignment",
            "template":  templates[0].name,
            "employee":  emps[0].name,
            "is_active": 1,
        }).insert(ignore_permissions=True)

    frappe.db.commit()


def _create_runs() -> None:
    assignments = frappe.get_all(
        "SOP Assignment",
        filters={"is_active": 1},
        fields=["name", "template", "employee"],
    )
    emp_user = {
        e.name: frappe.db.get_value("Pulse Employee", e.name, "user")
        for e in frappe.get_all("Pulse Employee", fields=["name", "user"])
    }
    emp_user = {k: v for k, v in emp_user.items() if v}

    today    = getdate()
    current  = START_DATE

    while current <= END_DATE:
        is_today = current == today
        for a in assignments:
            user = emp_user.get(a.employee)
            if not user:
                continue

            rate     = COMPLETION_RATE.get(user, 0.85)
            template = frappe.get_doc("SOP Template", a.template)

            if template.frequency_type == "Weekly" and current.weekday() != 0:
                continue
            if template.frequency_type == "Monthly" and current.day != 1:
                continue

            run_items = []
            for ci in template.checklist_items:
                completed = random.random() < rate
                status    = "Completed" if completed else ("Pending" if is_today else "Missed")
                run_items.append({
                    "checklist_item":   ci.description,
                    "weight":           ci.weight,
                    "item_type":        ci.item_type,
                    "status":           status,
                    "evidence_required": ci.evidence_required or "None",
                    "completed_at":     now() if completed and not is_today else None,
                })

            run_status = "Open" if is_today else ("Locked" if random.random() < 0.1 else "Closed")
            frappe.get_doc({
                "doctype":     "SOP Run",
                "template":    a.template,
                "employee":    a.employee,
                "period_date": current.isoformat(),
                "status":      run_status,
                "run_items":   run_items,
            }).insert(ignore_permissions=True)

        current = add_days(current, 1)

    frappe.db.commit()


def _create_score_snapshots() -> None:
    emp_scores = _compute_scores()
    now_dt     = now()

    for emp in frappe.get_all("Pulse Employee", fields=["name"]):
        emp_name = emp.name
        scores   = emp_scores.get(emp_name, {})

        for (period_type, period_key), (own, team, combined, total, completed) in scores.items():
            if frappe.db.exists(
                "Score Snapshot",
                {"employee": emp_name, "period_type": period_type, "period_key": period_key},
            ):
                continue
            frappe.get_doc({
                "doctype":         "Score Snapshot",
                "employee":        emp_name,
                "period_type":     period_type,
                "period_key":      period_key,
                "own_score":       own,
                "team_score":      team,
                "combined_score":  combined,
                "total_items":     total,
                "completed_items": completed,
                "computed_at":     now_dt,
            }).insert(ignore_permissions=True)

    frappe.db.commit()


def _compute_scores() -> dict:
    """Aggregate own/team/combined scores from SOP Runs per employee per day."""
    runs = frappe.get_all(
        "SOP Run",
        filters=[
            ["period_date", ">=", START_DATE.isoformat()],
            ["period_date", "<=", END_DATE.isoformat()],
        ],
        fields=["employee", "period_date", "total_items", "completed_items"],
    )

    emp_runs: dict[str, list] = {}
    for r in runs:
        emp_runs.setdefault(r.employee, []).append(r)

    hierarchy = {
        row["name"]: row["reports_to"]
        for row in frappe.get_all("Pulse Employee", fields=["name", "reports_to"])
    }
    children: dict[str, list] = {}
    for emp, parent in hierarchy.items():
        if parent:
            children.setdefault(parent, []).append(emp)

    result: dict = {}

    # Own scores per day
    for emp in frappe.get_all("Pulse Employee", pluck="name"):
        by_day: dict[date, tuple] = {}
        for r in emp_runs.get(emp, []):
            d = getdate(r.period_date) if r.period_date else None
            if not d:
                continue
            prev = by_day.get(d, (0, 0))
            by_day[d] = (prev[0] + (r.total_items or 0), prev[1] + (r.completed_items or 0))

        for d, (total, completed) in by_day.items():
            own = (completed / total) if total else 0
            result.setdefault(emp, {})[("Day", d.isoformat())] = (own, 0, own, total, completed)

    # Team scores (average of direct reports)
    for emp in frappe.get_all("Pulse Employee", pluck="name"):
        subs = children.get(emp, [])
        if not subs:
            continue
        for (pt, pk) in list(result.get(emp, {}).keys()):
            if pt != "Day":
                continue
            team_vals = [
                result.get(s, {}).get((pt, pk), (0, 0, 0, 0, 0))[2]
                for s in subs
            ]
            team_vals = [v for v in team_vals if v > 0]
            team      = sum(team_vals) / len(team_vals) if team_vals else 0
            own, _, _, total, completed = result[emp][(pt, pk)]
            combined  = (own + team) / 2 if team else own
            result[emp][(pt, pk)] = (own, team, combined, total, completed)

    return result


def _create_corrective_actions() -> None:
    runs_with_missed = frappe.get_all(
        "SOP Run",
        filters={"status": ["in", ["Closed", "Locked"]]},
        fields=["name", "employee"],
    )
    run_items = frappe.get_all(
        "SOP Run Item",
        filters={
            "parent": ["in", [r.name for r in runs_with_missed]],
            "status": "Missed",
        },
        fields=["parent", "checklist_item"],
    )

    by_run: dict[str, list] = {}
    for ri in run_items:
        by_run.setdefault(ri.parent, []).append(ri.checklist_item)

    supervisors = frappe.get_all(
        "Pulse Employee",
        filters={"pulse_role": "Supervisor"},
        pluck="name",
    )

    statuses   = (["Closed"] * 5 + ["Resolved"] * 4 + ["In Progress"] * 4 + ["Open"] * 5)
    priorities = (["Critical"] * 3 + ["High"] * 5 + ["Medium"] * 5 + ["Low"] * 5)
    random.shuffle(statuses)
    random.shuffle(priorities)

    created = 0
    for run_name, items in list(by_run.items())[:18]:
        if not items:
            continue
        run     = frappe.get_doc("SOP Run", run_name)
        sup     = random.choice(supervisors) if supervisors else run.employee
        status  = statuses[created % len(statuses)]
        priority = priorities[created % len(priorities)]
        desc    = f"Missed: {items[0][:50]}..."
        resolved = status in ("Closed", "Resolved")

        frappe.get_doc({
            "doctype":       "Corrective Action",
            "run":           run_name,
            "run_item_ref":  items[0][:140],
            "description":   desc,
            "status":        status,
            "assigned_to":   run.employee,
            "raised_by":     sup,
            "priority":      priority,
            "resolution":    "Resolved and verified." if resolved else None,
            "resolved_at":   now() if resolved else None,
        }).insert(ignore_permissions=True)
        created += 1

    frappe.db.commit()
