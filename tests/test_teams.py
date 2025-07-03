"""Unit tests for the team allocation logic using pytest and Faker."""

import random
from unittest import mock

import pandas as pd
import pytest
from faker import Faker

from team_former.make_teams import allocate_teams


def generate_random_preferences(
    student_ids, p_pos=0.4, p_neg=0.3, max_pos=3, max_neg=2
):
    """Generate random positive and negative preferences for students."""
    prefs_with = {s: [] for s in student_ids}
    prefs_not_with = {s: [] for s in student_ids}

    for s in student_ids:
        others = [o for o in student_ids if o != s]
        if random.random() < p_pos and others:
            prefs_with[s] = random.sample(
                others, k=random.randint(1, min(max_pos, len(others)))
            )
        if random.random() < p_neg and others:
            prefs_not_with[s] = random.sample(
                others, k=random.randint(1, min(max_neg, len(others)))
            )
    return prefs_with, prefs_not_with


@pytest.fixture
def fake_student_df_fixture():
    """Fixture to generate a fake student DataFrame with preferences."""
    fake = Faker()
    Faker.seed(1234)
    random.seed(1234)

    n = 100
    student_ids = [f"S{i+1}" for i in range(n)]
    pos_prefs, neg_prefs = generate_random_preferences(student_ids)

    students = []
    for sid in student_ids:
        students.append(
            {
                "Student_ID": sid,
                "first_name": fake.first_name(),
                "last_name": fake.last_name(),
                "email": fake.email(),
                "gender": fake.random_element(elements=("M", "F")),
                "wam": round(
                    fake.pyfloat(
                        left_digits=2,
                        right_digits=2,
                        positive=True,
                        min_value=50,
                        max_value=90,
                    ),
                    2,
                ),
                "lab": fake.random_int(min=1, max=4),
                "Prefer_With": ", ".join(pos_prefs[sid]) if pos_prefs[sid] else "",
                "Prefer_Not_With": ", ".join(neg_prefs[sid]) if neg_prefs[sid] else "",
            }
        )
    return pd.DataFrame(students)


def report_wam_balance(df_out):
    """Report per-team WAM averages and optionally check balance."""
    team_groups = df_out.groupby("team")
    team_wams = team_groups["wam"].mean()
    overall_mean = df_out["wam"].mean()

    print("\n📊 WAM balance report per team:")
    for team, avg_wam in team_wams.items():
        print(f"  Team {team}: avg WAM = {avg_wam:.2f}")
    print(f"\n🎯 Overall mean WAM: {overall_mean:.2f}")
    print(f"⚖️ Max deviation: {abs(team_wams - overall_mean).max():.2f}")


def test_allocate_teams_returns_df(request):
    """Check that allocate_teams returns a valid DataFrame with a team column."""
    fake_df = request.getfixturevalue("fake_student_df_fixture")
    with mock.patch("pandas.read_excel", return_value=fake_df), mock.patch(
        "pandas.DataFrame.to_excel"
    ):
        df_out = allocate_teams(
            input_file="fake.xlsx",
            sheet_name=0,
            output_file="output.xlsx",
            max_solve_time=40,
            wam_weight=0.05,
            pos_pref_weight=0.8,
            neg_pref_weight=0.8,
            min_team_size=3,
            max_team_size=5,
        )
        assert isinstance(df_out, pd.DataFrame)
        assert "team" in df_out.columns
        assert len(df_out) == len(fake_df)
        assert df_out["team"].notna().all()


def test_teams_have_valid_sizes(request):
    """Verify each team is within the size limits and report WAM balance."""
    fake_df = request.getfixturevalue("fake_student_df_fixture")
    with mock.patch("pandas.read_excel", return_value=fake_df), mock.patch(
        "pandas.DataFrame.to_excel"
    ):
        df_out = allocate_teams(
            input_file="fake.xlsx",
            sheet_name=0,
            output_file="output.xlsx",
            max_solve_time=40,
            wam_weight=0.05,
            pos_pref_weight=0.8,
            neg_pref_weight=0.8,
            min_team_size=3,
            max_team_size=5,
        )
        team_sizes = df_out.groupby("team").size()
        assert (team_sizes >= 3).all()
        assert (team_sizes <= 5).all()
        report_wam_balance(df_out)


def test_fake_student_df_content(request):
    """Verify the fake data fixture content and columns."""
    fake_df = request.getfixturevalue("fake_student_df_fixture")
    assert len(fake_df) == 100
    expected_cols = {
        "Student_ID",
        "first_name",
        "last_name",
        "email",
        "gender",
        "wam",
        "lab",
        "Prefer_With",
        "Prefer_Not_With",
    }
    assert set(fake_df.columns) == expected_cols
    assert fake_df["lab"].between(1, 4).all()
    assert fake_df["wam"].between(50, 90).all()


@pytest.mark.filterwarnings("ignore:R0914")
def test_preferences_satisfaction(request):
    """Check how many preferences are satisfied in the allocation."""
    fake_df = request.getfixturevalue("fake_student_df_fixture")
    with mock.patch("pandas.read_excel", return_value=fake_df), mock.patch(
        "pandas.DataFrame.to_excel"
    ):
        df_out = allocate_teams(
            input_file="fake.xlsx",
            sheet_name=0,
            output_file="output.xlsx",
            max_solve_time=40,
            wam_weight=0.05,
            pos_pref_weight=0.8,
            neg_pref_weight=0.8,
            min_team_size=3,
            max_team_size=5,
        )

        team_map = df_out.set_index("Student_ID")["team"].to_dict()

        pos_prefs = []
        neg_prefs = []

        for _, row in fake_df.iterrows():
            student = row["Student_ID"].strip()

            if pd.notna(row["Prefer_With"]) and row["Prefer_With"].strip():
                preferred = [
                    s.strip() for s in row["Prefer_With"].split(",") if s.strip()
                ]
                for p in preferred:
                    pos_prefs.append((student, p))

            if pd.notna(row["Prefer_Not_With"]) and row["Prefer_Not_With"].strip():
                not_preferred = [
                    s.strip() for s in row["Prefer_Not_With"].split(",") if s.strip()
                ]
                for np in not_preferred:
                    neg_prefs.append((student, np))

        pos_satisfied = sum(
            a in team_map and b in team_map and team_map[a] == team_map[b]
            for a, b in pos_prefs
        )
        neg_satisfied = sum(
            a in team_map and b in team_map and team_map[a] != team_map[b]
            for a, b in neg_prefs
        )

        assert pos_satisfied > 0, "No positive preferences satisfied"
        assert neg_satisfied > 0, "No negative preferences satisfied"
        print(f"Positive preferences satisfied: {pos_satisfied}/{len(pos_prefs)}")
        print(f"Negative preferences satisfied: {neg_satisfied}/{len(neg_prefs)}")
