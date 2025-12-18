import pandas as pd
import pandera.pandas as pa
from pandera import Check, Column, DataFrameSchema

TARGET = "default.payment.next.month"

SCHEMA = DataFrameSchema(
    {
        "LIMIT_BAL": Column(pa.Float, Check.ge(0), coerce=True),
        "SEX": Column(pa.Int, Check.isin([1, 2]), coerce=True),
        "EDUCATION": Column(pa.Int, Check.isin([1, 2, 3, 4]), coerce=True),  # 0/5/6 → 4
        "MARRIAGE": Column(pa.Int, Check.isin([1, 2, 3]), coerce=True),  # 0 → 3
        "AGE": Column(pa.Int, Check.between(18, 100), coerce=True),
        **{
            f"PAY_{k}": Column(pa.Int, Check.between(-2, 9), coerce=True)
            for k in [0, 2, 3, 4, 5, 6]
        },
        **{f"BILL_AMT{i}": Column(pa.Float, coerce=True) for i in range(1, 7)},
        **{f"PAY_AMT{i}": Column(pa.Float, Check.ge(0), coerce=True) for i in range(1, 7)},
        "utilization1": Column(pa.Float, nullable=True, coerce=True),
        "payment_ratio1": Column(pa.Float, nullable=True, coerce=True),
        "max_delay": Column(pa.Int, Check.between(-2, 9), coerce=True),
        TARGET: Column(pa.Int, Check.isin([0, 1]), coerce=True),
    },
    checks=[Check(lambda df: 0.05 <= df[TARGET].mean() <= 0.5, error="Аномальная доля класса-1")],
)


def validate_csv(path: str):
    df = pd.read_csv(path)
    SCHEMA.validate(df, lazy=True)
    return True
