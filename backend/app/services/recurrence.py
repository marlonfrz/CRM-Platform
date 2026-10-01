import calendar
from datetime import date, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Activity, ActivitySchedule
from app.models.activity import ActivityStatus
from app.models.activity_schedule import MonthlyMode, RecurrenceUnit
from app.schemas.activities import RecurrenceRequest


def _month_after(value: date, months: int) -> tuple[int, int]:
    index = value.year * 12 + value.month - 1 + months
    return index // 12, index % 12 + 1


def _monthly_date(schedule: ActivitySchedule, year: int, month: int) -> date:
    if schedule.monthly_mode == MonthlyMode.DAY_OF_MONTH.value:
        day = min(
            schedule.monthly_day or schedule.starts_on.day,
            calendar.monthrange(year, month)[1],
        )
        return date(year, month, day)
    weekday = schedule.monthly_weekday if schedule.monthly_weekday is not None else 0
    week = schedule.monthly_week or 1
    first_weekday, days = calendar.monthrange(year, month)
    day = 1 + (weekday - first_weekday) % 7 + (week - 1) * 7
    if day > days:
        day -= 7
    return date(year, month, day)


def next_occurrence(schedule: ActivitySchedule, current: date) -> date:
    interval = schedule.repeat_interval
    if schedule.repeat_unit == RecurrenceUnit.DAY.value:
        return current + timedelta(days=interval)
    if schedule.repeat_unit == RecurrenceUnit.WEEK.value:
        weekdays = {int(value) for value in (schedule.weekdays or "").split(",") if value}
        anchor = schedule.starts_on - timedelta(days=schedule.starts_on.weekday())
        candidate = current + timedelta(days=1)
        while True:
            week_index = (candidate - anchor).days // 7
            if candidate.weekday() in weekdays and week_index % interval == 0:
                return candidate
            candidate += timedelta(days=1)
    year, month = _month_after(current, interval)
    return _monthly_date(schedule, year, month)


def schedule_from_rule(
    *,
    rule: RecurrenceRequest,
    starts_on: date,
    **values: object,
) -> ActivitySchedule:
    return ActivitySchedule(
        **values,
        starts_on=starts_on,
        repeat_unit=rule.repeat_unit.value,
        repeat_interval=rule.repeat_interval,
        weekdays=",".join(str(day) for day in sorted(rule.weekdays)) or None,
        monthly_mode=rule.monthly_mode.value if rule.monthly_mode else None,
        monthly_day=rule.monthly_day,
        monthly_week=rule.monthly_week,
        monthly_weekday=rule.monthly_weekday,
        ends_on=rule.ends_on,
        last_materialized_on=starts_on,
        active=True,
    )


def occurrence_from_schedule(schedule: ActivitySchedule, scheduled_for: date) -> Activity:
    return Activity(
        organization_id=schedule.organization_id,
        client_id=schedule.client_id,
        user_id=schedule.created_by_user_id,
        assigned_to_user_id=schedule.assigned_to_user_id,
        department_id=schedule.department_id,
        activity_type_id=schedule.activity_type_id,
        schedule_id=schedule.id,
        title=schedule.title,
        description=schedule.description,
        next_action=schedule.next_action,
        scheduled_for=scheduled_for,
        status=ActivityStatus.PENDING.value,
        occurred_at=None,
        completed_at=None,
    )


def materialize_next(session: AsyncSession, schedule: ActivitySchedule) -> Activity | None:
    following = next_occurrence(schedule, schedule.last_materialized_on)
    if schedule.ends_on is not None and following > schedule.ends_on:
        schedule.active = False
        return None
    schedule.last_materialized_on = following
    activity = occurrence_from_schedule(schedule, following)
    session.add(activity)
    return activity


async def materialize_schedules(
    session: AsyncSession,
    *,
    organization_id: UUID,
    client_id: UUID | None = None,
    today: date | None = None,
) -> None:
    current_day = today or date.today()
    statement = select(ActivitySchedule).where(
        ActivitySchedule.organization_id == organization_id,
        ActivitySchedule.active.is_(True),
        ActivitySchedule.last_materialized_on <= current_day,
    )
    if client_id is not None:
        statement = statement.where(ActivitySchedule.client_id == client_id)
    schedules = await session.scalars(statement.with_for_update())
    for schedule in schedules:
        while schedule.active and schedule.last_materialized_on <= current_day:
            materialize_next(session, schedule)
    await session.flush()
