# Pulse

**Execution visibility and process compliance for operations teams.**

![Pulse screenshot](screenshot.png)

Pulse is a **Process KPI Engine** that helps operations leaders see how well frontline teams execute standard procedures—daily checklists, SOPs, and corrective actions—with role-based dashboards, team roll-ups, and organizational insights.

---

## What Is Pulse?

Pulse sits between **task execution** and **business outcomes**. It answers:

- **Are our standard procedures being followed?** (completion rates, missed items)
- **How does performance roll up by team, department, and branch?** (scores, trends)
- **Where do we need to focus?** (corrective actions, most-missed items, top/bottom performers)

It is built for **operations-heavy environments**: QSR chains, retail, facilities, healthcare support, logistics, and any setting where consistent execution of checklists and SOPs drives quality and compliance.

---

## Where and How It Can Be Used

| Context | How Pulse Helps |
|--------|--------------------------|
| **Multi-site operations** | Compare branches and departments; drill from org-level metrics to individual employees. |
| **Compliance & audit** | Track completion and evidence of SOP execution over time; corrective action trail. |
| **Frontline managers** | One view of direct reports’ scores and open tasks; “My Team” and “All Teams” for leaders. |
| **Leadership** | Insights: trends, department/branch comparison, score distribution, day-of-week patterns. |
| **Configurable roles** | Map your org titles (e.g. “Shift Manager”, “Cleaner”) to system roles and permissions. |

Deployment is typically **one app on a Frappe site**, with optional integration to your existing HR or identity system via the User and PM Employee link.

---

## How It Differs From Other Tools

| | **Pulse** | **Project management (PM) tools** | **Task managers** | **BPM / workflow engines** |
|---|------------------|-----------------------------------|-------------------|----------------------------|
| **Focus** | Execution of **recurring** procedures (SOPs, checklists) | One-off **projects** and deliverables | Ad-hoc **tasks** and to-dos | **Process design** and automation |
| **Unit of work** | SOP runs (template × employee × period) | Projects, milestones, issues | Tasks, subtasks | Processes, activities, cases |
| **Metrics** | Completion %, scores, trends by org/branch/dept | Burndown, velocity, status | Done vs pending | Cycle time, SLA, throughput |
| **Audience** | Operations, area managers, leadership | PMs, delivery teams | Individuals, small teams | Process owners, IT |
| **Typical use** | “Did we do the opening checklist today?” | “Is the launch on track?” | “What do I need to do?” | “How long does approval take?” |

Pulse does **not** replace Jira, Asana, or Camunda. It complements them by focusing on **recurring operational execution** and **role-based visibility** over hierarchies and geography.

---

## Use Cases

1. **QSR / restaurant chains**  
   Opening/closing checklists, hygiene and safety SOPs, daily cash and stock checks. Area managers see branch and team scores; leadership sees trends and most-missed items.

2. **Retail and multi-location**  
   Store readiness, compliance checklists, and standard procedures. Compare stores and regions; drill into underperformers.

3. **Facilities and operations**  
   Rounds, inspections, and maintenance checklists. Supervisors see team completion; managers see site and department roll-ups.

4. **Healthcare support (non-clinical)**  
   Housekeeping, equipment checks, and protocol adherence. Configurable roles (e.g. “Ward Supervisor”) and department/branch filters.

5. **Any hierarchy with SOPs**  
   Define templates, assign to roles/employees, run daily/weekly/monthly. Scores and insights respect your org structure (reports-to, department, branch).

---

## Features

- **Dashboard** — Personal score (own + team), period selector (Day/Week/Month), team bar chart, most-missed tasks (for managers).
- **My Tasks** — Today’s SOP runs and checklist items; complete, miss, or defer with notes.
- **Team** — “My Team” (direct reports) and “All Teams” (org or subtree) with scores; links to user profiles.
- **Operations** — Hierarchical tree of employees with scores; expand by level; navigate to profile and run breakdown.
- **Insights** — Score trends, department/branch comparison, top/bottom performers, template performance, completion trend, corrective actions, day-of-week heatmap, score distribution, most-missed items. Filters: date range, department, branch; clickable department/branch bars for drill-down and filtered employee table.
- **User profile** — Score, team list, run breakdown, and (for operators/supervisors) operational checklists.
- **SOP templates** — Define checklists, frequency, owner role, department; assign to employees.
- **Configurable roles** — Business roles (e.g. Operator, Supervisor, Area Manager) mapped to system roles; display alias (e.g. “Shift Manager”) in the UI.

---

## User Roles (System Roles)

| Role | Typical use | Visibility |
|------|-------------|------------|
| **PM User** | Operator / frontline | Own dashboard, own tasks, own profile |
| **PM Manager** | Supervisor | + My Team, SOP templates (read), corrective actions (create) |
| **PM Leader** | Area / regional manager | + All Teams (subtree), Operations tree, Insights |
| **PM Executive** | Leadership | + All Teams (org-wide), full Insights |
| **PM Admin** | Setup and config | Full access; PM Role, departments, templates |

Business titles (e.g. “Shift Manager”, “Cleaner”) are configured in **PM Role** and shown as **alias** in the UI; permissions are driven by the linked **system role**.

---

## Tech Stack

- **Backend:** [Frappe Framework](https://frappeframework.com/) (v16)
- **Frontend:** React 19, Vite, Tailwind CSS 4, Shadcn UI, Recharts
- **API:** Frappe whitelisted methods; frontend uses `frappe-js-sdk`

---

## Installation

Requires a [Frappe Bench](https://frappeframework.com/docs/user/en/installation) (v16).

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app https://github.com/tridz-dev/pulse 
bench install-app pulse
```

After migration, default PM Roles and departments are created via **after_install**.

### Demo data

The quickest way to see Pulse in action is to load the built-in demo dataset — a realistic
QSR chain with three branches, 19 employees across a four-level hierarchy, six SOP templates,
and ~40 days of historical runs, scores, and corrective actions.

**Load or remove via bench CLI:**

```bash
bench --site <site> pulse-load-demo
bench --site <site> pulse-clear-demo
```

**Or via `bench execute`:**

```bash
bench --site <site> execute pulse.demo.seed.seed_demo_data
bench --site <site> execute pulse.demo.seed.clear_demo_data
```

**What you get:**

| What | Detail |
|---|---|
| 19 demo users | Password `Demo@123` on every account |
| 4-level org hierarchy | Chairman → MD → Area Managers → Supervisors → Operators |
| 3 branches + HQ | Branch N1, Branch N2, Branch S1, and HQ |
| 6 SOP templates | 5 daily checklists + 1 weekly deep clean |
| ~400 SOP runs | 40-day window ending yesterday — data is always current |
| ~390 score snapshots | Daily own / team / combined scores per employee |
| 18 corrective actions | Varied priority and status |

**First-time setup:** the Frappe setup wizard includes a **"Load demo data"** checkbox on the
Pulse slide — check it to seed automatically on wizard completion.

**In-app:** System Manager and Pulse Admin users see a **"Load demo data"** card on the
Dashboard when no employees exist; clicking it enqueues the seed in the background.

For the full account list, org chart, SOP template details, and per-user completion rates,
see [`pulse/demo/README.md`](pulse/demo/README.md).

---


Pre-commit runs: ruff, eslint, prettier, pyupgrade.

---

## License

**GNU Affero General Public License v3.0 (AGPL-3.0)**  

You may use, modify, and distribute this software under the terms of the AGPL-3.0. See [LICENSE](LICENSE) or [license.txt](license.txt) in the repository for the full text. If you distribute a modified version over a network, you must make the source available to users under the same license.

---

## Contact

**Tridz**  
Email: **pulse@tridz.com**

For feature requests, support, or deployment guidance, reach out to the address above.
