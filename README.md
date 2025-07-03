# Teamformer

Teamformer builds student teams for you. The primary objective is to form as few teams as are needed while ensuring constraints are met, and encouraging WAM (weighted average mark/GPA) balance across teams. The system is a wrapper around a CP-SAT solver using Google OR-Tools.

Constraint handling includes:

✅ Each student is assigned to exactly one team

✅ Each team has between min and max students

✅ No team has only one student of a given gender (currently only M/F; other self-reported categories are ignored for balancing, but won't break anything)

✅ The number of teams used is minimized

✅ Students are only assigned to teams in the same lab as them

✅ Deviation from average WAM across the class is penalised

✅ Student preferences are favoured (positive and negative preferences now supported!)

The output is an Excel sheet with students and teams. Team numbers may not be sequential (drawn from 1\:max\_teams).

---

### Data structure

Teamformer expects data in a spreadsheet like this (fake example):

|   | first\_name | last\_name | email | gender | wam  | lab | Prefer\_With | Prefer\_Not\_With |
| - | ----------- | ---------- | ----- | ------ | ---- | --- | ------------ | ----------------- |
| 0 | Mark        | Johnson    | ...   | M      | 51.1 | 3   | S2, S3       | S4                |
| 1 | Donald      | Walker     | ...   | M      | 60.0 | 1   |              |                   |
| 2 | Sarah       | Rhodes     | ...   | F      | 76.6 | 1   | S1           | S3                |
| 3 | Steven      | Miller     | ...   | M      | 54.2 | 2   |              |                   |
| 4 | Javier      | Johnson    | ...   | M      | 75.3 | 4   |              |                   |

**Columns used:**

* `gender`
* `wam`
* `lab`
* `Prefer_With` (optional): comma-separated list of Student\_IDs the student wants to work with
* `Prefer_Not_With` (optional): comma-separated list of Student\_IDs the student prefers not to work with

---

### Install

```bash
pip install -e .
```

---

### Run

```bash
team_former --input_file=students.xlsx --sheet_name=0 --output_file=teams.xlsx --wam_weight=0.05 --pos_pref_weight=0.8 --neg_pref_weight=0.8 --min_team_size=3 --max_team_size=5 --max_solve_time=30
```

---

### How to get a good solution

Depending on your class sizes, demographics and lab distribution, you may struggle to find a feasible solution. Options to address this include:

* Increase the max solve time — it may just be a matter of waiting longer
* Reduce or remove the WAM weight penalty
* Adjust the minimum team size — sometimes team balance is infeasible
* Adjust positive or negative preference weights (e.g., set `pos_pref_weight=0.5` if you want preferences to have less influence)

---

### Preference handling

When using preference columns, Teamformer will attempt to:

* **Keep students together** if listed in `Prefer_With`, unless it conflicts with other constraints.
* **Avoid assigning students together** if listed in `Prefer_Not_With`.

Preferences are not strictly enforced (they are "soft" constraints), but they strongly influence the solution when weights are set high.

---
