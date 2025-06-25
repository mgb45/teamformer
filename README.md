# Teamformer


Teamformer builds student teams for you. The primary objective is to form as few teams as are needed while ensuring constraints are met, and encouraging WAM (weighted average mark/gpa) balance across teams. The system is basically a wrapper around a CP-SAT solver using Google OR-Tools.

Constraint handling includes:

✅ Each student is assigned to exactly one team 

✅ Each team has between min and max students

✅ No team has only one student of a given gender (current only M/F, if other self-report categories these are ignored and not balanced, but does not break anything)

✅ The number of teams used is minimized

✅ Students are only assigned to teams in the same lab as them

✅ Deviation from average WAM across class is penalised

❌ Student preferences are favoured (Not yet implemented)

The output is an excel sheet with students and teams. Team numbers may not be sequential (drawn from 1:max_teams).

### Data structure
Team former assumes data is in a spreadsheet that looks something like (fake data):

|    | first_name   | last_name   | email                     | gender   |   wam |   lab |
|---:|:-------------|:------------|:--------------------------|:---------|------:|------:|
|  0 | Mark         | Johnson     | ...  | M        | 51.13 |     3 |
|  1 | Donald       | Walker      | ...  | M        | 60.04 |     1 |
|  2 | Sarah        | Rhodes      | ...  | F        | 76.57 |     1 |
|  3 | Steven       | Miller      | ...  | M        | 54.22 |     2 |
|  4 | Javier       | Johnson     | ... | M        | 75.26 |     4 |

**Only the gender, wam and lab columns are used.**

### Install

```
pip install -e .
```
### Run

```
team_former --input_file=students.xlsx --sheet_name=0 --output_file=teams.xlsx --wam_weight=0.05 --min_team_size=3 --max_team_size=5 --max_solve_time=30
```

### How to get a good solution

Depending on your class sizes, demographics and lab distribution, you may struggle to find a feasible solution. Options to address this include:
* Increase the max solve time, it may just be a matter of waiting a bit longer
* Reduce or remove the wam weight penalty
* Reduce the minimimun team size, it may be that the balance of students is infeasible.
