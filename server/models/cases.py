from pydantic import BaseModel, field_validator


class CriminalCase(BaseModel):
    id: int
    serial_no: str | None = None
    fir_no: str | None = None
    case_no: str | None = None
    court: str | None = None
    ipc_sections: str | None = None
    other_acts: str | None = None
    charges_framed: bool = False
    charge_date: str | None = None
    is_serious: bool = False

    @field_validator("charges_framed", "is_serious", mode="before")
    @classmethod
    def int_to_bool(cls, v: int | bool | None) -> bool:
        """
        SQLite stores booleans as INTEGER (0/1).
        This validator casts them so routers never see raw ints.
        """
        if v is None:
            return False
        return bool(v)