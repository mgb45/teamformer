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


def create_fake_df(include_wam=True, include_lab=True, include_prefs=True, n=50):
    """Helper to create a fake student DataFrame with optional columns."""
    fake = Faker()
    Faker.seed(1234)
    random.seed(1234)

    student_ids = [f"S{i+1}" for i in range(n)]
    pos_prefs, neg_prefs = generate_random_preferences(student_ids)

    students = []
    for sid in student_ids:
        row = {
            "Student_ID": sid,
            "first_name": fake.first_name(),
            "last_name": fake.last_name(),
            "email": fake.email(),
            "gender": fake.random_element(elements=("M", "F")),
        }
        if include_wam:
            row["wam"] = round(
                fake.pyfloat(
                    left_digits=2,
                    right_digits=2,
                    positive=True,
                    min_value=50,
                    max_value=90,
                ),
                2,
            )
        if include_lab:
            row["lab"] = fake.random_int(min=1, max=4)
        if include_prefs:
            row["Prefer_With"] = ", ".join(pos_prefs[sid]) if pos_prefs[sid] else ""
            row["Prefer_Not_With"] = ", ".join(neg_prefs[sid]) if neg_prefs[sid] else ""
        students.append(row)

    return pd.DataFrame(students)


@pytest.mark.parametrize(
    "include_wam, include_lab, include_prefs",
    [
        (True, True, True),  # All columns
        (False, True, True),  # No wam
        (True, False, True),  # No lab
        (True, True, False),  # No preferences
        (False, False, False),  # Only Student_ID, gender
    ],
)
def test_allocate_with_various_columns(include_wam, include_lab, include_prefs):
    """Test allocation with various combinations of optional columns."""
    fake_df = create_fake_df(
        include_wam=include_wam,
        include_lab=include_lab,
        include_prefs=include_prefs,
        n=50,
    )

    with mock.patch("pandas.read_excel", return_value=fake_df), mock.patch(
        "pandas.DataFrame.to_excel"
    ):
        df_out = allocate_teams(
            input_file="fake.xlsx",
            sheet_name=0,
            output_file="output.xlsx",
            max_solve_time=30,
            wam_weight=0.1 if include_wam else 0,
            pos_pref_weight=0.5 if include_prefs else 0,
            neg_pref_weight=0.5 if include_prefs else 0,
            min_team_size=3,
            max_team_size=6,
        )
        assert isinstance(df_out, pd.DataFrame)
        assert "team" in df_out.columns
        assert len(df_out) == len(fake_df)
        assert df_out["team"].notna().all()

        # Check team sizes
        team_sizes = df_out.groupby("team").size()
        assert (team_sizes >= 3).all()
        assert (team_sizes <= 6).all()


def test_fake_df_structure():
    """Verify that create_fake_df generates expected columns based on options."""
    # All columns
    df_all = create_fake_df(True, True, True)
    assert "wam" in df_all.columns
    assert "lab" in df_all.columns
    assert "Prefer_With" in df_all.columns
    assert "Prefer_Not_With" in df_all.columns

    # No wam
    df_no_wam = create_fake_df(False, True, True)
    assert "wam" not in df_no_wam.columns

    # No lab
    df_no_lab = create_fake_df(True, False, True)
    assert "lab" not in df_no_lab.columns

    # No prefs
    df_no_prefs = create_fake_df(True, True, False)
    assert "Prefer_With" not in df_no_prefs.columns
    assert "Prefer_Not_With" not in df_no_prefs.columns

    # Only minimal
    df_minimal = create_fake_df(False, False, False)
    for col in ["wam", "lab", "Prefer_With", "Prefer_Not_With"]:
        assert col not in df_minimal.columns
    assert "Student_ID" in df_minimal.columns
    assert "gender" in df_minimal.columns
