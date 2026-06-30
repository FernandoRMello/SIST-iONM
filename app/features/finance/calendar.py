import calendar
from datetime import date, timedelta


def calculate_due_date(period: str, due_day: int, holidays: set[date]) -> date:
    year_text, month_text = period.split("-", 1)
    year, month = int(year_text), int(month_text)
    if not 1 <= due_day <= 31:
        raise ValueError("Dia de vencimento deve estar entre 1 e 31.")
    last_day = calendar.monthrange(year, month)[1]
    due_date = date(year, month, min(due_day, last_day))
    while due_date.weekday() >= 5 or due_date in holidays:
        due_date += timedelta(days=1)
    return due_date
