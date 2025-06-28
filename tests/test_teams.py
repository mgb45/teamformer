"""Unit tests for the team allocation logic using pytest and Faker."""

from unittest import mock

import pandas as pd
import pytest
from faker import Faker

from team_former.make_teams import allocate_teams


@pytest.fixture
def fake_student_df_fixture():
    """Generate a fake student dataframe with Faker."""
    fake = Faker()
    Faker.seed(1234)

    students = []
    for _ in range(100):
        students.append(
            {
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
            }
        )

    return pd.DataFrame(students)


def test_allocate_teams_returns_df(df_in=fake_student_df_fixture):
    """Check that allocate_teams returns a valid DataFrame with a team column."""
    with mock.patch("pandas.read_excel", return_value=df_in), mock.patch(
        "pandas.DataFrame.to_excel"
    ):

        df_out = allocate_teams(
            input_file="fake.xlsx",
            sheet_name=0,
            output_file="output.xlsx",
            max_solve_time=40,
            wam_weight=0.05,
            min_team_size=3,
            max_team_size=5,
        )

        assert isinstance(df_out, pd.DataFrame)
        assert "team" in df_out.columns
        assert len(df_out) == len(df_in)
        assert df_out["team"].notna().all()


def test_teams_have_valid_sizes(df_in=fake_student_df_fixture):
    """Verify each team is within the size limits."""
    with mock.patch("pandas.read_excel", return_value=df_in), mock.patch(
        "pandas.DataFrame.to_excel"
    ):

        df_out = allocate_teams(
            input_file="fake.xlsx",
            sheet_name=0,
            output_file="output.xlsx",
            max_solve_time=40,
            wam_weight=0.05,
            min_team_size=3,
            max_team_size=5,
        )

        team_sizes = df_out.groupby("team").size()
        assert (team_sizes >= 3).all()
        assert (team_sizes <= 5).all()


def test_fake_student_df_content(df_in=fake_student_df_fixture):
    """Verify the fake data fixture is correct."""
    assert len(df_in) == 100
    assert set(df_in.columns) == {
        "first_name",
        "last_name",
        "email",
        "gender",
        "wam",
        "lab",
    }
    assert df_in["lab"].between(1, 4).all()
    assert df_in["wam"].between(50, 90).all()
