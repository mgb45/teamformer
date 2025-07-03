# pylint: disable=too-many-arguments, too-many-locals, too-many-statements, too-many-branches

"""Team allocation using constraint programming with OR-Tools."""

import fire
import pandas as pd
from ortools.sat.python import cp_model


def parse_preferences(df):
    """Parse positive and negative preferences from the DataFrame columns."""
    id_to_index = {row["Student_ID"]: idx for idx, row in df.iterrows()}

    positive_prefs = []
    negative_prefs = []

    has_pos = "Prefer_With" in df.columns
    has_neg = "Prefer_Not_With" in df.columns

    for _, row in df.iterrows():
        student = row["Student_ID"].strip()

        # Positive preferences
        if has_pos and pd.notna(row["Prefer_With"]) and row["Prefer_With"].strip():
            preferred = [s.strip() for s in row["Prefer_With"].split(",") if s.strip()]
            for target in preferred:
                if target in id_to_index:
                    positive_prefs.append((student, target))

        # Negative preferences
        if (
            has_neg
            and pd.notna(row["Prefer_Not_With"])
            and row["Prefer_Not_With"].strip()
        ):
            not_preferred = [
                s.strip() for s in row["Prefer_Not_With"].split(",") if s.strip()
            ]
            for target in not_preferred:
                if target in id_to_index:
                    negative_prefs.append((student, target))

    positive_prefs = [(id_to_index[a], id_to_index[b]) for (a, b) in positive_prefs]
    negative_prefs = [(id_to_index[a], id_to_index[b]) for (a, b) in negative_prefs]

    return positive_prefs, negative_prefs


def allocate_teams(
    *,
    input_file="students.xlsx",
    sheet_name=0,
    output_file="class_teams.xlsx",
    wam_weight=0.05,
    pos_pref_weight=0.05,
    neg_pref_weight=0.1,
    min_team_size=4,
    max_team_size=5,
    max_solve_time=60,
):
    """
    Allocate students into balanced teams based on optional WAM, gender, lab, and preferences.

    Args:
        input_file (str): Path to the Excel file with student data.
        sheet_name (int or str): Sheet index or name.
        output_file (str): Output Excel file with team assignments.
        wam_weight (float): Weight for WAM balancing in the objective.
        pos_pref_weight (float): Weight for positive preference balancing.
        neg_pref_weight (float): Weight for negative preference balancing.
        min_team_size (int): Minimum number of students per team.
        max_team_size (int): Maximum number of students per team.
        max_solve_time (int): Solver timeout in seconds.
    """
    student_df = pd.read_excel(input_file, sheet_name=sheet_name)
    print(student_df.head())

    students = student_df.to_dict(orient="index")
    num_students = len(students)
    max_teams = num_students // min_team_size

    has_wam = "wam" in student_df.columns
    has_lab = "lab" in student_df.columns
    has_gender = "gender" in student_df.columns

    if has_wam:
        wams = student_df["wam"].astype(int).values
        global_avg_wam = int(sum(wams) / len(wams))

    if has_lab:
        lab_ids = sorted(set(student_df["lab"].astype(int).values))
        student_labs = student_df["lab"].astype(int).values

    if has_gender:
        genders = student_df["gender"].values

    pos_preferences, neg_preferences = parse_preferences(student_df)

    model = cp_model.CpModel()

    # Variables
    assign = {
        (i, team): model.NewBoolVar(f"assign_{i}_{team}")
        for i in range(num_students)
        for team in range(max_teams)
    }

    team_used = [model.NewBoolVar(f"team_used_{team}") for team in range(max_teams)]

    if has_lab:
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

    if has_lab:
        for team in range(max_teams):
            model.AddExactlyOne(lab_team[team, lab] for lab in lab_ids)

        for i in range(num_students):
            for team in range(max_teams):
                model.Add(lab_team[team, student_labs[i]] == 1).OnlyEnforceIf(
                    assign[i, team]
                )

    if has_gender:
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

    # Objective terms
    squared_deviation_terms = []
    if has_wam:
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

    pref_bonus_terms = []
    for i, j in pos_preferences:
        for team in range(max_teams):
            together = model.NewBoolVar(f"prefer_{i}_{j}_team_{team}")
            model.AddBoolAnd([assign[i, team], assign[j, team]]).OnlyEnforceIf(together)
            model.AddBoolOr(
                [assign[i, team].Not(), assign[j, team].Not()]
            ).OnlyEnforceIf(together.Not())
            pref_bonus_terms.append(together)

    negative_terms = []
    for i, j in neg_preferences:
        for team in range(max_teams):
            both = model.NewBoolVar(f"neg_pref_{i}_{j}_team_{team}")
            model.AddBoolAnd([assign[i, team], assign[j, team]]).OnlyEnforceIf(both)
            model.AddBoolOr(
                [assign[i, team].Not(), assign[j, team].Not()]
            ).OnlyEnforceIf(both.Not())
            negative_terms.append(both)

    # Objective
    objective_terms = [sum(team_used)]

    if has_wam and wam_weight > 0:
        objective_terms.append(int(wam_weight * 1000) * sum(squared_deviation_terms))
    if pos_pref_weight > 0:
        objective_terms.append(-pos_pref_weight * sum(pref_bonus_terms))
    if neg_pref_weight > 0:
        objective_terms.append(neg_pref_weight * sum(negative_terms))

    model.Minimize(sum(objective_terms))

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
