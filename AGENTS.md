# Pulse — Agent Reference

Frappe app + React SPA that tracks SOP execution across a multi-branch organisation
and converts daily operational activity into measurable, hierarchical performance signals.

**Bench root:** `/workspace/development/edge16`
**Site:** `pulse.localhost`
**App path:** `apps/pulse/`
**Frontend:** `apps/pulse/frontend/`

---

## Concept

Pulse closes the "accountability gap" between ground-level task execution and C-Suite KPIs.

```
Operator completes checklist items
        ↓
SOP Run is scored (own_score)
        ↓
Supervisor inherits team average (team_score)
        ↓
Area Manager inherits their subtree average
        ↓
Executive sees org-wide health
```

Every missed step degrades the combined score of every manager in the reporting line — making
failure visible at any level in real time.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | Frappe 16 (Python) |
| Database | MariaDB (via Frappe ORM + raw SQL for analytics) |
| Frontend | React 19, React Router 7, Vite 5 |
| Styling | Tailwind CSS 4, shadcn/ui (Radix), Base UI |
| Charts | Recharts |
| Gauges | Custom SVG (`Gauge.tsx`), `requestAnimationFrame` |
| Icons | Lucide React |
| Fonts | Geist Variable (body), DM Mono (metrics) |
| Frappe SDK | `frappe-js-sdk` |

---

## Repository layout

```
pulse/
├── AGENTS.md                   # ← this file
├── frontend/                   # React SPA
│   └── src/
│       ├── pages/              # Top-level route pages
│       ├── components/         # Shared UI components
│       ├── services/           # Frappe API client wrappers
│       ├── types/index.ts      # All TypeScript types
│       └── lib/frappe-sdk.ts   # frappe-js-sdk singleton
└── pulse/                      # Frappe app
    ├── api/                    # Whitelisted Python methods
    │   ├── auth.py             # get_current_employee
    │   ├── permissions.py      # Row-level query conditions
    │   ├── tasks.py            # Run CRUD + item completion
    │   ├── scores.py           # Score calculation
    │   ├── operations.py       # Hierarchy tree + breakdown
    │   ├── insights.py         # Analytics (SQL aggregations)
    │   ├── templates.py        # SOP template catalog
    │   └── demo.py             # Admin demo data API
    ├── commands.py             # bench CLI commands
    ├── hooks.py                # Frappe hooks: scheduler, permissions, install
    ├── install.py              # after_install: roles, default records
    ├── tasks.py                # Scheduled jobs
    ├── demo/                   # Canonical demo data
    │   ├── data.py             # Static definitions (users, templates, rates)
    │   ├── seed.py             # seed_demo_data(), clear_demo_data()
    │   └── README.md           # Data table + usage
    ├── seed/                   # Backward-compat shim → imports from demo/
    ├── pulse_core/doctype/     # Core transactional DocTypes
    └── pulse_setup/doctype/    # Setup/config DocTypes
```

---

## DocTypes

### Setup DocTypes (`pulse_setup`)

#### Pulse Role
Maps business role names to Frappe system roles.

| Field | Type | Notes |
|---|---|---|
| `role_name` | Data | PK display name (e.g. "Operator") |
| `level` | Int | Hierarchy level (1=Operator … 4=Executive) |
| `alias` | Data | Short display label (shown in UI) |
| `description` | Small Text | |
| `system_role` | Link→Role | Frappe Role used for permission checks |

Default records created at install:

| role_name | level | system_role |
|---|---|---|
| Operator | 1 | Pulse User |
| Supervisor | 2 | Pulse Manager |
| Area Manager | 3 | Pulse Leader |
| Executive | 4 | Pulse Executive |

#### Pulse Department
Simple master for department grouping.

| Field | Type |
|---|---|
| `department_name` | Data (PK) |
| `description` | Small Text |
| `is_active` | Check |

#### Pulse Employee
Central employee profile linked to a Frappe User.

| Field | Type | Notes |
|---|---|---|
| `employee_name` | Data | Display name |
| `user` | Link→User | Frappe login account |
| `pulse_role` | Link→Pulse Role | Business role |
| `branch` | Data | Branch / location |
| `department` | Link→Pulse Department | |
| `reports_to` | Link→Pulse Employee | Builds org hierarchy |
| `is_active` | Check | |
| `avatar_url` | Data | Profile image |

Auto-naming: `PLS-EMP-####`

---

### Core DocTypes (`pulse_core`)

#### SOP Template
Master definition of a repeating checklist.

| Field | Type | Notes |
|---|---|---|
| `title` | Data | |
| `department` | Link→Pulse Department | |
| `frequency_type` | Select | Daily / Weekly / Monthly / Custom |
| `owner_role` | Link→Pulse Role | Which role executes this SOP |
| `active_from` | Date | |
| `active_to` | Date | Blank = open-ended |
| `is_active` | Check | |
| `checklist_items` | Table→SOP Checklist Item | Child rows |

#### SOP Checklist Item _(child of SOP Template)_

| Field | Type | Notes |
|---|---|---|
| `description` | Data | Step text |
| `sequence` | Int | Ordering |
| `weight` | Float | Score weight (default 1.0) |
| `item_type` | Select | Checkbox / Numeric / Photo |
| `evidence_required` | Select | None / Photo |

#### SOP Assignment
Links a SOP Template to a specific Pulse Employee.

| Field | Type |
|---|---|
| `template` | Link→SOP Template |
| `employee` | Link→Pulse Employee |
| `is_active` | Check |

The scheduler reads active assignments to generate daily/weekly/monthly runs.

#### SOP Run
One execution instance of a template for one employee on one date.

| Field | Type | Notes |
|---|---|---|
| `template` | Link→SOP Template | |
| `employee` | Link→Pulse Employee | |
| `period_date` | Date | |
| `status` | Select | Open / Closed / Locked |
| `total_items` | Int | Set by before_save hook |
| `completed_items` | Int | Counted from run_items |
| `progress` | Float | % 0–100 |
| `closed_at` | Datetime | Set when status→Closed |
| `run_items` | Table→SOP Run Item | |

**Status lifecycle:**

```
Open  ──[employee completes]──→  Closed
Open  ──[day passes, overdue]──→  Locked  (Pending items → Missed)
```

#### SOP Run Item _(child of SOP Run)_

| Field | Type | Notes |
|---|---|---|
| `checklist_item` | Data | Step description (denormalised) |
| `weight` | Float | Copied from template |
| `item_type` | Select | Checkbox / Numeric / Photo |
| `status` | Select | Pending / Completed / Missed |
| `completed_at` | Datetime | |
| `numeric_value` | Float | For Numeric items |
| `notes` | Small Text | Free-text notes |
| `evidence` | Attach | File upload (planned) |
| `evidence_required` | Select | None / Photo |

#### Score Snapshot
Cached per-employee score for a period. Written by the hourly scheduler and by the seed.

| Field | Type | Notes |
|---|---|---|
| `employee` | Link→Pulse Employee | |
| `period_type` | Select | Day / Week / Month |
| `period_key` | Data | "YYYY-MM-DD" for Day; "YYYY-MM-DD to YYYY-MM-DD" for Week/Month |
| `own_score` | Float | 0–1: this employee's item completion |
| `team_score` | Float | 0–1: avg combined_score of direct reports |
| `combined_score` | Float | Average of own + team (or just own if no reports) |
| `total_items` | Int | Items in scope |
| `completed_items` | Int | |
| `computed_at` | Datetime | |

#### Corrective Action
Raised when a run has missed checklist items.

| Field | Type | Notes |
|---|---|---|
| `run` | Link→SOP Run | Source run |
| `run_item_ref` | Data | Missed step description |
| `description` | Small Text | |
| `status` | Select | Open / In Progress / Resolved / Closed |
| `assigned_to` | Link→Pulse Employee | Employee accountable |
| `raised_by` | Link→Pulse Employee | Supervisor who raised it |
| `priority` | Select | Critical / High / Medium / Low |
| `resolution` | Small Text | |
| `resolved_at` | Datetime | |

---

## Scoring Logic

```
own_score = completed_items / total_items   (for period)

team_score = mean(combined_score of active direct reports with load)

combined_score:
  if team_score > 0 and own total_items > 0:  (own + team) / 2
  elif team_score > 0:                         team_score
  else:                                        own_score
```

Scores propagate **bottom-up**: leaf employees have `team_score = 0`, combined = own.
Each level's combined_score feeds its manager's team_score.

Score brackets used in insights distribution histogram:

| Bracket | Range |
|---|---|
| Exceptional | ≥ 90% |
| Strong | 80–89% |
| Moderate | 60–79% |
| At Risk | 40–59% |
| Critical | < 40% |

---

## Permission Model

Five Frappe roles (created at install):

| Frappe Role | Business Role | Visibility scope |
|---|---|---|
| Pulse User | Operator | Own SOP Runs only |
| Pulse Manager | Supervisor | Own + direct reports |
| Pulse Leader | Area Manager | Full subtree (recursive) |
| Pulse Executive | Executive | Entire organisation |
| Pulse Admin | Admin | Everything (same as Administrator) |

Row-level conditions are registered in `hooks.py → permission_query_conditions`:

```python
permission_query_conditions = {
    "SOP Run":          "pulse.api.permissions.sop_run_conditions",
    "Score Snapshot":   "pulse.api.permissions.score_snapshot_conditions",
    "Corrective Action":"pulse.api.permissions.corrective_action_conditions",
}
```

The condition functions (`permissions.py`) inject WHERE clauses into Frappe's list queries
based on the logged-in user's employee record and role.

---

## API (Whitelisted Methods)

All callable as `/api/method/pulse.api.<module>.<method>` with a valid Frappe session.

### `auth.py`
| Method | Purpose |
|---|---|
| `get_current_employee()` | Current user's Pulse Employee + role info. Returns synthetic admin profile for System Manager/Pulse Admin without an employee record |

### `tasks.py`
| Method | Purpose |
|---|---|
| `get_my_runs(date?)` | Today's SOP Runs for the current user |
| `get_runs_for_employee(employee, date?)` | Runs for a specific employee (manager access) |
| `get_run_details(run_name)` | Full run + all items for checklist runner |
| `update_run_item(run_item_name, status, notes?, numeric_value?)` | Toggle item Pending↔Completed. Validates ownership |
| `complete_run(run_name)` | Mark run Closed |

### `scores.py`
| Method | Purpose |
|---|---|
| `get_score_for_user(employee, date?, period_type?)` | Single employee score snapshot |
| `get_team_scores(manager_employee, date?, period_type?)` | Scores for direct reports |
| `get_all_team_scores(employee, date?, period_type?)` | Org-wide (Executive) or subtree (Area Manager) |
| `get_failure_analytics(manager_employee, date?)` | Top 5 most-missed tasks across subtree, last 30 days |

### `operations.py`
| Method | Purpose |
|---|---|
| `get_operations_overview(top_employee, date?, period_type?)` | Full hierarchy tree with scores. Recursive. |
| `get_user_run_breakdown(employee, date?, period_type?)` | Runs grouped by template for the ScoreBreakdown sheet |
| `get_hierarchy_breakdown(top_employee, date?, period_type?)` | Full hierarchy with per-user breakdown (heavy) |

### `insights.py`
All accept `department`, `branch`, `employee` filters. Scope is enforced by role.

| Method | Returns |
|---|---|
| `get_insight_departments()` | List of department names |
| `get_insight_branches()` | Distinct branches in scope |
| `get_score_trends(start?, end?, period_type?, ...)` | `[{date, avg_score, employee_count}]` |
| `get_department_comparison(date?, period_type?, ...)` | `[{department, avg_score, headcount}]` |
| `get_branch_comparison(date?, period_type?, ...)` | `[{branch, avg_score, headcount}]` |
| `get_top_bottom_performers(date?, period_type?, limit?, ...)` | `{top: [...], bottom: [...]}` |
| `get_template_performance(start?, end?, ...)` | Completion rate per SOP template |
| `get_completion_trend(start?, end?, ...)` | Daily `{date, completed, total, rate}` |
| `get_corrective_action_summary(...)` | `{by_status, by_priority, avg_resolution_hours}` |
| `get_day_of_week_heatmap(start?, end?, ...)` | `[{day_name, day_num, avg_rate}]` |
| `get_score_distribution(date?, period_type?, ...)` | `[{bracket, count}]` histogram |
| `get_most_missed_items(start?, end?, limit?, ...)` | `[{checklist_item, template_title, department, misses}]` |
| `get_employees_by_department(department, date?, period_type?)` | Employees + scores for a department |
| `get_employees_by_branch(branch, date?, period_type?)` | Employees + scores for a branch |

### `templates.py`
| Method | Purpose |
|---|---|
| `get_all_templates()` | List all active SOP Templates |
| `get_template_items(template_name)` | Ordered checklist items for a template |

### `demo.py`
| Method | Purpose |
|---|---|
| `get_demo_status()` | Whether current user can load/clear demo and whether demo exists |
| `install_demo_data(enqueue?)` | Load demo data (admin only, optionally background) |
| `clear_demo_data()` | Remove all demo data (admin only) |

---

## Scheduler Tasks

Registered in `hooks.py → scheduler_events`:

| Frequency | Function | What it does |
|---|---|---|
| `daily` | `pulse.tasks.daily` | `generate_daily_runs()` + `lock_overdue_runs()` |
| `hourly` | `pulse.tasks.hourly` | `cache_score_snapshots()` — upsert today's Score Snapshot for all employees |
| `weekly` | `pulse.tasks.weekly` | `generate_weekly_runs()` — creates runs on Mondays only |
| `monthly` | `pulse.tasks.monthly` | `generate_monthly_runs()` — creates runs on the 1st only |

**generate_*_runs:** reads all active `SOP Assignment` records where the linked template
matches the frequency. For each assignment, creates one `SOP Run` if none exists yet for
that (template, employee, date) triple.

**lock_overdue_runs:** finds all `Open` runs with `period_date < today`, sets all `Pending`
items to `Missed`, sets run status to `Locked`.

**cache_score_snapshots:** calls `_calculate_score_snapshot()` for every active employee
and upserts the `Score Snapshot` DocType. Live calculation is still used for API calls
(snapshots are a read-optimisation for Insights SQL queries).

---

## Frontend Pages & Routes

Base path: `/pulse` (configured via `website_route_rules` in `hooks.py`)

| Route | Page | Role access | Purpose |
|---|---|---|---|
| `/` | `Dashboard.tsx` | All | Own score gauge, today's run summary, failure analytics |
| `/tasks` | `MyTasks.tsx` | All | Today's SOP Runs; tap to open checklist runner |
| `/team` | `Team.tsx` | Manager+ | Direct reports with scores and status |
| `/operations` | `Operations.tsx` | Leader+ | Full org tree; date/period picker; drill by node |
| `/operations/:userId` | `UserProfile.tsx` | Leader+ | Per-employee detail: runs, scores, charts |
| `/insights` | `Insights.tsx` | Leader+ | Analytics: trends, heatmap, distribution, top/bottom |
| `/templates` | `Templates.tsx` | All | SOP template catalog; printable checklists |

### Key Components

| Component | Location | Purpose |
|---|---|---|
| `AppLayout` | `components/layout/` | Sidebar + topbar shell, theme toggle |
| `Sidebar` | `components/layout/` | Role-aware nav links |
| `Gauge` | `components/shared/` | SVG needle gauge, `requestAnimationFrame` animation |
| `ScoreBreakdown` | `components/shared/` | Slide-over sheet showing run breakdown by template |
| `InsightsFilters` | `components/insights/` | Department / branch / employee / date filter bar |

### Data flow

```
frappe-js-sdk (lib/frappe-sdk.ts)
    ↓
services/*.ts  →  pulse.api.*  (whitelisted Frappe methods)
    ↓
React pages / components
```

`AuthContext.tsx` wraps the app and calls `get_current_employee()` on mount.
Unauthenticated users are redirected to the Frappe login page.

---

## Data Flow Diagram

```
                    ┌─────────────────────────────────┐
                    │        Frappe Scheduler          │
                    │  daily / hourly / weekly /       │
                    │  monthly                         │
                    └──────────────┬──────────────────┘
                                   │ generates
                    ┌──────────────▼──────────────────┐
  SOP Template ───► │           SOP Run                │ ◄─── SOP Assignment
  (checklist)       │  Open → Closed (by employee)     │      (template × employee)
                    │        → Locked (overdue)        │
                    └──────────────┬──────────────────┘
                                   │ contains
                    ┌──────────────▼──────────────────┐
                    │         SOP Run Item             │
                    │  Pending → Completed / Missed    │
                    └──────────────┬──────────────────┘
                                   │ aggregated by
                    ┌──────────────▼──────────────────┐
                    │        Score Snapshot            │
                    │  own / team / combined (0–1)     │
                    └──────────────┬──────────────────┘
                                   │ rolled up
                    ┌──────────────▼──────────────────┐
                    │      Pulse Employee hierarchy    │
                    │  Operator → Supervisor → AM →   │
                    │  Executive                       │
                    └──────────────┬──────────────────┘
                                   │ consumed by
                    ┌──────────────▼──────────────────┐
                    │        React SPA                 │
                    │  Dashboard / Operations /        │
                    │  Insights / MyTasks / Team       │
                    └─────────────────────────────────┘
```

---

## Bench Commands

```bash
# Demo data
bench --site pulse.localhost pulse-load-demo
bench --site pulse.localhost pulse-clear-demo

# Or via execute
bench --site pulse.localhost execute pulse.demo.seed.seed_demo_data
bench --site pulse.localhost execute pulse.demo.seed.clear_demo_data

# Run scheduler tasks manually
bench --site pulse.localhost execute pulse.tasks.daily
bench --site pulse.localhost execute pulse.tasks.generate_daily_runs
bench --site pulse.localhost execute pulse.tasks.lock_overdue_runs
bench --site pulse.localhost execute pulse.tasks.cache_score_snapshots

# Check data counts
bench --site pulse.localhost mariadb -e "
  SELECT 'Pulse Employee' as t, COUNT(*) FROM \`tabPulse Employee\`
  UNION ALL SELECT 'SOP Template', COUNT(*) FROM \`tabSOP Template\`
  UNION ALL SELECT 'SOP Assignment', COUNT(*) FROM \`tabSOP Assignment\`
  UNION ALL SELECT 'SOP Run', COUNT(*) FROM \`tabSOP Run\`
  UNION ALL SELECT 'SOP Run Item', COUNT(*) FROM \`tabSOP Run Item\`
  UNION ALL SELECT 'Score Snapshot', COUNT(*) FROM \`tabScore Snapshot\`
  UNION ALL SELECT 'Corrective Action', COUNT(*) FROM \`tabCorrective Action\`;"
```

---

## Demo Data

See `pulse/demo/README.md` for the full account table.

| DocType | Count | Notes |
|---|---|---|
| User | 19 | All with `Demo@123` |
| Pulse Role | 4 | Operator / Supervisor / Area Manager / Executive |
| Pulse Department | 7 | Kitchen, Front-of-House, Procurement, Finance, Operations, Management, Security |
| Pulse Employee | 19 | Full 4-level hierarchy across 3 branches + HQ |
| SOP Template | 6 | 5 daily + 1 weekly |
| SOP Checklist Item | 22 | Embedded in templates |
| SOP Assignment | 12 | Template × employee pairs |
| SOP Run | ~400 | 40 days of history (relative window ending yesterday) |
| SOP Run Item | ~1 500 | Per-step outcomes |
| Score Snapshot | ~390 | Daily aggregates |
| Corrective Action | 18 | Varied status/priority |

**Org hierarchy (QSR chain):**

```
Ramesh Agarwal (Chairman · Executive · HQ)
└── Priya Sharma (MD · Executive · HQ)
    ├── Vikram Patel (RM North · Area Manager · North Region)
    │   ├── Rahul Nair (BM N1 · Supervisor · Branch N1)
    │   │   └── Kavitha Raj (Sup N1 · Supervisor · Branch N1)
    │   │       ├── Arun Bhat   (Chef N1 · Operator · Branch N1)
    │   │       ├── Pooja Reddy (Chef N2 · Operator · Branch N2)
    │   │       ├── Ravi Verma  (Cashier N1 · Operator · Branch N1)
    │   │       └── Mohan Das   (Cleaner N1 · Operator · Branch N1)
    │   └── Meera Iyer (BM N2 · Supervisor · Branch N2)
    │       └── Deepak Singh (Sup N2 · Supervisor · Branch N2)
    │           └── Neha Gupta (Cashier N2 · Operator · Branch N2)
    ├── Anita Das (RM South · Area Manager · South Region)
    │   └── Suresh Kumar (BM S1 · Supervisor · Branch S1)
    │       └── Lakshmi Menon (Sup S1 · Supervisor · Branch S1)
    │           ├── Sunita Devi (Cleaner S1 · Operator · Branch S1)
    │           └── Vijay Singh (Driver · Operator · Branch S1)
    ├── Rajesh Mehta  (Purchase · Operator · HQ)
    └── Anjali Kapoor (Finance · Operator · HQ)
```

---

## Install Flow

1. `bench get-app pulse <repo>`
2. `bench --site <site> install-app pulse`
3. `after_install` fires → creates 5 system roles, 4 Pulse Role records, 3 default departments
4. Setup wizard prompts to optionally load demo data (`setup_wizard_complete` → `pulse.setup.setup_wizard.setup_demo`)
5. Or post-install: `bench --site <site> pulse-load-demo`

---

## Open Items

- [ ] Evidence / file upload for Photo checklist items
- [ ] Real-time run updates (WebSocket / Server-Sent Events)
- [ ] AI failure prediction from historical trends
- [ ] Offline PWA with sync on reconnect
- [ ] End-to-end test suite
