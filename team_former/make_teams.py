import pandas as pd
from ortools.sat.python import cp_model
import fire

def allocate_teams(
    input_file='students.xlsx',
    sheet_name=0,
    output_file='class_teams.xlsx',
    wam_weight=0.05,
    min_team_size=4,
    max_team_size=5,
    max_solve_time=60,
):
    df = pd.read_excel(input_file, sheet_name=sheet_name)
    
    print(df.head())
    
    students = df.to_dict(orient='index')
    
    num_students = len(students)
    
    genders = df['gender']
    wam = df['wam'].astype(int).values
    labs = sorted(set(df['lab'].astype(int).values))
    student_labs = df['lab'].astype(int).values
    
    global_avg_wam = sum(wam) // len(wam)
    
    max_teams = num_students // min_team_size

    model = cp_model.CpModel()

    # Variables: assign[i, t] = 1 if student i is in team t
    assign = {
        (i, t): model.NewBoolVar(f"assign_{i}_{t}")
        for i in range(num_students)
        for t in range(max_teams)
    }

    # Each student in exactly one team
    for i in range(num_students):
        model.Add(sum(assign[i, t] for t in range(max_teams)) == 1)

    # Each team must have between min and max students if used
    team_used = [model.NewBoolVar(f"used_{t}") for t in range(max_teams)]
    for t in range(max_teams):
        team_size = sum(assign[i, t] for i in range(num_students))
        model.Add(team_size <= max_team_size)
        model.Add(team_size >= min_team_size).OnlyEnforceIf(team_used[t])
        model.Add(team_size == 0).OnlyEnforceIf(team_used[t].Not())

    # Define lab assignment per team
    lab_team = {(t, l): model.NewBoolVar(f'team_{t}_lab_{l}') for t in range(max_teams) for l in labs}
    for t in range(max_teams):
        model.AddExactlyOne(lab_team[t, l] for l in labs)
        
    for i in range(num_students):
        for t in range(max_teams):
            model.Add(lab_team[t, student_labs[i]] == 1).OnlyEnforceIf(assign[i, t])

    # Gender constraint: no single student of a gender on a team
    for t in range(max_teams):
        males = [assign[i, t] for i in range(num_students) if genders[i] == "M"]
        females = [assign[i, t] for i in range(num_students) if genders[i] == "F"]
        if males:
            model.Add(sum(males) != 1)
        if females:
            model.Add(sum(females) != 1)

    # WAM balance objective
    squared_deviation_terms = []
    for t in range(max_teams):
        wam_sum = model.NewIntVar(0, 100 * max_team_size, f"wam_sum_{t}")
        team_size = model.NewIntVar(0, max_team_size, f"team_size_{t}")
        model.Add(team_size == sum(assign[i, t] for i in range(num_students)))
        model.Add(wam_sum == sum(wam[i] * assign[i, t] for i in range(num_students)))
        diff = model.NewIntVar(-500, 500, f"wam_diff_{t}")
        model.Add(diff == wam_sum - team_size * global_avg_wam)
        sq = model.NewIntVar(0, 250000, f"squared_diff_{t}")
        model.AddMultiplicationEquality(sq, [diff, diff])
        squared_deviation_terms.append(sq)

    model.Minimize(
        sum(team_used) + int(wam_weight * 1000) * sum(squared_deviation_terms)
    )

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = max_solve_time
    status = solver.Solve(model)

    if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        for t in range(max_teams):
            members = [i for i in range(num_students) if solver.Value(assign[i, t])]
            if members:
                print(f"Team {t + 1}:")
                ave_wam = 0
                for i in members:
                    print(f"  Name {students[i]['first_name']} (Gender: {students[i]['gender']}, WAM: {students[i]['wam']}, lab: {students[i]['lab']})")
                    ave_wam += students[i]['wam']
                print(f'Average WAM: {ave_wam/len(members):.2f}\n')
    else:
        print("No feasible solution found.")
        return

    team_alloc = []
    for i in range(num_students):
        for t in range(max_teams):
            if solver.Value(assign[i, t]):
                team_alloc.append(t)
    df['team'] = team_alloc
    df.to_excel(output_file, index=False)
    print(f"\n✅ Teams saved to {output_file}")


# # Basic usage
# python team_allocator.py --input_file=students.xlsx

# With custom parameters
# python team_allocator.py --input_file=students.xlsx --alpha=0.1 --max_solve_time=60 --min_team_size=3 --max_team_size=6

def main():
    fire.Fire(allocate_teams)

if __name__ == '__main__':
    main()
