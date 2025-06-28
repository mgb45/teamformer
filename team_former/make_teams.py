# pylint: disable=too-many-arguments, too-many-locals, too-many-statements, too-many-branches

"""Team allocation using constraint programming with OR-Tools."""

import fire
import pandas as pd
from ortools.sat.python import cp_model


def allocate_teams(
    *,
    input_file="students.xlsx",
    sheet_name=0,
    output_file="class_teams.xlsx",
    wam_weight=0.05,
    min_team_size=4,
    max_team_size=5,
    max_solve_time=60,
):
    """
    Allocate students into balanced teams based on WAM, gender, and lab constraints.

    Args:
        input_file (str): Path to the Excel file with student data.
        sheet_name (int or str): Sheet index or name.
        output_file (str): Output Excel file with team assignments.
        wam_weight (float): Weight for WAM balancing in the objective.
        min_team_size (int): Minimum number of students per team.
        max_team_size (int): Maximum number of students per team.
        max_solve_time (int): Solver timeout in seconds.
    """
    student_df = pd.read_excel(input_file, sheet_name=sheet_name)
    print(student_df.head())

    students = student_df.to_dict(orient="index")
    num_students = len(students)
    genders = student_df["gender"]
    wams = student_df["wam"].astype(int).values
    lab_ids = sorted(set(student_df["lab"].astype(int).values))
    student_labs = student_df["lab"].astype(int).values
    global_avg_wam = sum(wams) // len(wams)
    max_teams = num_students // min_team_size

    model = cp_model.CpModel()

    # Variables
    assign = {
        (i, team): model.NewBoolVar(f"assign_{i}_{team}")
        for i in range(num_students)
        for team in range(max_teams)
    }

    team_used = [model.NewBoolVar(f"team_used_{team}") for team in range(max_teams)]
    lab_team = {
        (team, lab): model.NewBoolVar(f"team_{team}_lab_{lab}")
        for team in range(max_teams)
        for lab in lab_ids
    }

    # Constraints
    for i in range(num_students):
        model.Add(sum(assign[i, team] for team in range(max_teams)) == 1)

    for team in range(max_teams):
        team_size = sum(assign[i, team] for i in range(num_students))
        model.Add(team_size <= max_team_size)
        model.Add(team_size >= min_team_size).OnlyEnforceIf(team_used[team])
        model.Add(team_size == 0).OnlyEnforceIf(team_used[team].Not())

    for team in range(max_teams):
        model.AddExactlyOne(lab_team[team, lab] for lab in lab_ids)

    for i in range(num_students):
        for team in range(max_teams):
            model.Add(lab_team[team, student_labs[i]] == 1).OnlyEnforceIf(
                assign[i, team]
            )

    for team in range(max_teams):
        male_students = [
            assign[i, team] for i in range(num_students) if genders[i] == "M"
        ]
        female_students = [
            assign[i, team] for i in range(num_students) if genders[i] == "F"
        ]
        if male_students:
            model.Add(sum(male_students) != 1)
        if female_students:
            model.Add(sum(female_students) != 1)

    # Objective: minimize number of teams + balance WAM
    squared_deviation_terms = []
    for team in range(max_teams):
        wam_sum = model.NewIntVar(0, 100 * max_team_size, f"wam_sum_{team}")
        size_var = model.NewIntVar(0, max_team_size, f"team_size_{team}")
        model.Add(size_var == sum(assign[i, team] for i in range(num_students)))
        model.Add(
            wam_sum == sum(wams[i] * assign[i, team] for i in range(num_students))
        )
        diff = model.NewIntVar(-500, 500, f"wam_diff_{team}")
        model.Add(diff == wam_sum - size_var * global_avg_wam)
        squared_diff = model.NewIntVar(0, 250000, f"squared_diff_{team}")
        model.AddMultiplicationEquality(squared_diff, [diff, diff])
        squared_deviation_terms.append(squared_diff)

    model.Minimize(
        sum(team_used) + int(wam_weight * 1000) * sum(squared_deviation_terms)
    )

    # Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_solve_time
    status = solver.Solve(model)

    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        print("No feasible solution found.")
        return None

    final_teams = [-1] * num_students
    team_count = 0
    for team in range(max_teams):
        members = [i for i in range(num_students) if solver.Value(assign[i, team])]
        if members:
            team_count += 1
            for student in members:
                final_teams[student] = team

    student_df["team"] = final_teams
    student_df.to_excel(output_file, index=False)
    print(f"\n✅ {team_count} teams formed.")
    print(f"📄 Teams saved to {output_file}")
    return student_df


def main():
    """Command-line interface wrapper."""
    fire.Fire(allocate_teams)


if __name__ == "__main__":
    main()
