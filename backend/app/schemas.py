from datetime import date, time
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

Status = Literal["enrolled", "on_leave", "graduating", "graduated"]
SourceCode = Literal["SCNU_MAIN", "SCNU_SW", "SCNU_AI"]
Category = Literal["contest", "education", "scholarship", "career", "startup", "overseas", "volunteer", "other"]

class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)

class EmailInput(StrictModel):
    email: EmailStr
    @field_validator("email")
    @classmethod
    def normalize_email(cls, value):
        return str(value).strip().casefold()

class Credentials(EmailInput):
    password: str = Field(min_length=12, max_length=128)

class LoginInput(EmailInput):
    password: str = Field(min_length=1, max_length=128)

class TokenInput(StrictModel):
    token: str = Field(min_length=32, max_length=256)

class ResetInput(TokenInput):
    password: str = Field(min_length=12, max_length=128)

class PasswordInput(StrictModel):
    password: str = Field(min_length=1, max_length=128)

class MessageOut(BaseModel):
    message: str

class UserOut(BaseModel):
    id: str
    email: str
    email_verified: bool
    is_admin: bool
    onboarding_complete: bool

class LoginOut(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_at: int
    user: UserOut

class InterestOut(BaseModel):
    id: str
    name: str
    type: Literal["field", "activity"]

class ProfileInput(StrictModel):
    department: str = Field(min_length=2, max_length=80)
    grade: int = Field(ge=1, le=6)
    academic_status: Status
    interest_ids: list[str] = Field(max_length=30)
    expected_version: int | None = Field(default=None, ge=0)

    @field_validator("department")
    @classmethod
    def clean_department(cls, value):
        value = value.strip()
        if len(value) < 2 or any(ord(c) < 32 for c in value):
            raise ValueError("Invalid department")
        return value

    @field_validator("interest_ids")
    @classmethod
    def deduplicate(cls, value):
        return sorted(set(value))

class ProfileOut(BaseModel):
    user_id: str
    department: str | None
    grade: int | None
    academic_status: Status | None
    interests: list[InterestOut]
    onboarding_complete: bool
    version: int
    updated_at: int

class Schedule(StrictModel):
    kind: Literal["application", "event"]
    label: str = Field(max_length=120)
    start_date: date | None
    end_date: date | None
    start_time: time | None
    end_time: time | None
    evidence: str = Field(max_length=3000)

    @model_validator(mode="after")
    def chronological(self):
        if self.start_time is not None and self.start_date is None:
            raise ValueError("start_time requires start_date")
        if self.end_time is not None and self.end_date is None:
            raise ValueError("end_time requires end_date")
        if self.start_time and self.start_time.tzinfo or self.end_time and self.end_time.tzinfo:
            raise ValueError("Schedule times are local Asia/Seoul wall times, without offset.")
        if self.start_date and self.end_date:
            if self.end_date < self.start_date:
                raise ValueError("End precedes start")
            if self.end_date == self.start_date and self.start_time and self.end_time:
                if self.end_time < self.start_time:
                    raise ValueError("End time precedes start time")
        return self

class Prize(StrictModel):
    status: Literal["present", "none", "not_stated"]
    description: str | None = Field(max_length=1500)
    evidence: str | None = Field(max_length=3000)

class Mileage(StrictModel):
    system: str = Field(min_length=1, max_length=100)
    points_text: str | None = Field(max_length=100)
    condition: str | None = Field(max_length=1500)
    evidence: str = Field(max_length=3000)

class AnalysisData(StrictModel):
    # All fields are required for a strict JSON-schema extraction.
    category: Category
    field_ids: list[str] = Field(max_length=20)
    activity_ids: list[str] = Field(max_length=20)
    tags: list[str] = Field(max_length=20)
    target_text: str | None = Field(max_length=3000)
    target_departments: list[str] = Field(max_length=50)
    target_grades: list[int] = Field(max_length=6)
    target_statuses: list[Status] = Field(max_length=4)
    all_departments: bool
    all_grades: bool
    eligibility_confirmed: bool
    summary_lines: list[str] = Field(min_length=3, max_length=3)
    schedules: list[Schedule] = Field(max_length=20)
    prize: Prize
    mileages: list[Mileage] = Field(max_length=20)
    application_method: str | None = Field(max_length=1500)
    confidence: float = Field(ge=0, le=1)

    @field_validator("target_grades")
    @classmethod
    def grade_range(cls, values):
        if any(x < 1 or x > 6 for x in values):
            raise ValueError("Grade must be 1..6")
        return sorted(set(values))

    @model_validator(mode="after")
    def consistency(self):
        if self.all_departments and self.target_departments:
            raise ValueError("Cannot be all departments and restricted departments")
        if self.all_grades and self.target_grades:
            raise ValueError("Cannot be all grades and restricted grades")
        if self.eligibility_confirmed and not self.target_text:
            raise ValueError("Confirmed eligibility requires source target text")
        if self.prize.status != "not_stated" and not self.prize.evidence:
            raise ValueError("Stated prize status requires evidence")
        return self

class AnalysisOut(BaseModel):
    provider: str
    status: str
    data: AnalysisData
    warnings: list[str]
    analyzed_at: int

class AttachmentOut(BaseModel):
    name: str
    url: str | None

class ScorePart(BaseModel):
    criterion: str
    score: float
    max_score: float
    reason: str | None

class RecommendationOut(BaseModel):
    score: float
    grade: str
    reasons: list[str]
    breakdown: list[ScorePart]
    policy_version: str

class NoticeCard(BaseModel):
    id: int
    title: str
    source_code: SourceCode
    source_name: str
    posted_date: date
    original_url: str
    category: str
    summary_lines: list[str]
    deadline_date: date | None
    deadline_at: int | None
    d_day: int | None
    deadline_label: str
    is_closed: bool
    is_bookmarked: bool
    needs_review: bool
    recommendation: RecommendationOut | None

class NoticeDetail(NoticeCard):
    body_text: str
    attachments: list[AttachmentOut]
    content_hash: str
    image_only: bool
    analysis: AnalysisOut
    fetched_at: int

class NoticePage(BaseModel):
    items: list[NoticeCard]
    total: int
    page: int
    page_size: int
    profile_version: int | None = None

class SourceOut(BaseModel):
    code: SourceCode
    name: str
    list_url: str
    enabled: bool
    last_success_at: int | None

class CalendarItem(BaseModel):
    id: str
    notice_id: int
    title: str
    kind: Literal["application", "event"]
    label: str
    start_date: date | None
    end_date: date | None
    start_time: time | None
    end_time: time | None
    display_start: date
    display_end: date
    is_partial: bool
    continues_before_month: bool
    continues_after_month: bool

class UndatedItem(BaseModel):
    notice_id: int
    title: str
    label: str

class CalendarOut(BaseModel):
    month: str
    timezone: Literal["Asia/Seoul"] = "Asia/Seoul"
    end_inclusive: bool = True
    events: list[CalendarItem]
    undated: list[UndatedItem]

class CrawlInput(StrictModel):
    sources: list[SourceCode] = Field(default_factory=lambda: ["SCNU_MAIN", "SCNU_SW", "SCNU_AI"], min_length=1, max_length=3)
    pages: int = Field(default=1, ge=1, le=3)
    max_notices: int = Field(default=20, ge=1, le=50)
    max_age_days: int = Field(default=60, ge=1, le=365)
    @field_validator("sources")
    @classmethod
    def unique_sources(cls, value):
        return list(dict.fromkeys(value))

class CrawlJobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    status: str
    parameters: dict
    result: dict | None
    error_code: str | None
    attempts: int
    created_at: int
    started_at: int | None
    finished_at: int | None

class ManualAnalysisInput(StrictModel):
    expected_content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    analysis: AnalysisData

class ErrorInfo(BaseModel):
    code: str
    message: str
    details: list[dict]
    request_id: str

class ErrorOut(BaseModel):
    error: ErrorInfo
