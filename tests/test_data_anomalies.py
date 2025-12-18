import pandas as pd
import pytest

from src.data.validation import SCHEMA


def test_schema_fails_on_out_of_range():
    df = pd.read_csv("data/processed/train.csv")
    bad = df.copy()
    bad.loc[0, "SEX"] = 3
    with pytest.raises(Exception):
        SCHEMA.validate(bad, lazy=True)


def test_schema_fails_on_nan_in_int():
    df = pd.read_csv("data/processed/train.csv")
    bad = df.copy()
    bad.loc[0, "AGE"] = None
    with pytest.raises(Exception):
        SCHEMA.validate(bad, lazy=True)
