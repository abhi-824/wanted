from __future__ import annotations

from pydantic import BaseModel, field_validator


class ParliamentRecord(BaseModel):
    """
    PRS MPTrack row for a single MP (identity fields omitted — see MPDetail).

    Activity fields (attendance, debates, questions, private_member_bills and
    their national/state averages) are None for ministers, the Speaker and the
    Leader of the Opposition, who do not participate in those activities.
    """

    prs_id: int
    gender: str | None = None
    house: str | None = None
    membership_type: str | None = None
    term_label: str | None = None
    term_number: int | None = None
    term_start: str | None = None
    term_end: str | None = None
    in_office: bool = True
    education_level: str | None = None
    education_details: str | None = None
    attendance: float | None = None
    debates: int | None = None
    questions: int | None = None
    private_member_bills: int | None = None
    national_avg_attendance: float | None = None
    national_avg_debates: float | None = None
    national_avg_questions: float | None = None
    national_avg_pmb: float | None = None
    state_avg_attendance: float | None = None
    state_avg_debates: float | None = None
    state_avg_questions: float | None = None
    state_avg_pmb: float | None = None
    note: str | None = None
    data_period_start: str | None = None
    data_period_end: str | None = None
    source: str | None = None

    @field_validator("in_office", mode="before")
    @classmethod
    def int_to_bool(cls, v: int | bool | None) -> bool:
        if v is None:
            return True
        return bool(v)
