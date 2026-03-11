from __future__ import annotations

import difflib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Protocol

from dietary_guardian.domain.reminders.enums import MetricType, ReminderChannel, ReminderState, ReminderType
from dietary_guardian.domain.reminders.models import (
    DEFAULT_THRESHOLD_RULES,
    FoodRecord,
    MetricReading,
    Reminder,
    ReminderDispatchResult,
    ReminderEvent,
    ThresholdRule,
    utc_now_iso,
)


class ReminderRepository(Protocol):
    def save_reminder(self, reminder: Reminder) -> None: ...
    def update_state(self, reminder_id: str, state: ReminderState) -> None: ...
    def get_reminder(self, reminder_id: str) -> Optional[dict[str, Any]]: ...
    def log_confirmation(self, reminder_id: str, is_taken: bool, timestamp: str) -> None: ...


class OutboxRepository(Protocol):
    def enqueue(self, event: ReminderEvent) -> None: ...
    def fetch_due_events(self, now: str, limit: int = 50) -> list[ReminderEvent]: ...
    def mark_sent(self, event_id: str, provider_msg_id: Optional[str] = None) -> None: ...
    def mark_failed(self, event_id: str, reason: str) -> None: ...


class MetricReadingRepository(Protocol):
    def log_metric_reading(self, reading: MetricReading) -> None: ...
    def get_last_metric_reading(self, user_id: str, metric_type: str) -> Optional[dict[str, Any]]: ...


class FoodRecordRepository(Protocol):
    def log_food_record(self, record: FoodRecord) -> None: ...
    def get_latest_food_record(self, user_id: str, meal_type: Optional[str] = None) -> Optional[dict[str, Any]]: ...


class DeliveryPort(Protocol):
    def send(self, event: ReminderEvent) -> ReminderDispatchResult: ...


class DrugKnowledgePort(Protocol):
    def get_drug_info(self, query: str) -> Optional[dict[str, Any]]: ...


@dataclass(slots=True)
class ReminderService:
    reminder_repo: ReminderRepository
    outbox_repo: OutboxRepository
    metric_repo: MetricReadingRepository
    food_repo: FoodRecordRepository
    delivery: DeliveryPort
    drug_knowledge: DrugKnowledgePort
    default_channel: str = ReminderChannel.TELEGRAM.value

    def _create_and_enqueue(
        self,
        *,
        user_id: str,
        reminder_type: ReminderType,
        message: str,
        scheduled_at: Optional[str] = None,
        payload: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Reminder:
        reminder = Reminder.create(
            user_id=user_id,
            reminder_type=reminder_type,
            message=message,
            scheduled_at=scheduled_at,
            payload=payload or {},
        )
        self.reminder_repo.save_reminder(reminder)

        event_payload = reminder.to_record()
        event = ReminderEvent.create(
            user_id=user_id,
            reminder_id=reminder.reminder_id,
            reminder_type=reminder.reminder_type,
            payload=event_payload,
            scheduled_at=reminder.scheduled_at,
            channel=channel or self.default_channel,
            correlation_id=correlation_id,
        )
        self.outbox_repo.enqueue(event)
        self.reminder_repo.update_state(reminder.reminder_id, ReminderState.ENQUEUED)
        reminder.mark(ReminderState.ENQUEUED)
        return reminder

    def _metric_label_cn(self, metric_type: MetricType | str) -> str:
        mapping = {
            MetricType.HEART_RATE.value: "心率",
            MetricType.BLOOD_GLUCOSE.value: "血糖",
            MetricType.HEART_RATE: "心率",
            MetricType.BLOOD_GLUCOSE: "血糖",
        }
        return mapping.get(metric_type, str(metric_type))

    def _meal_label_cn(self, meal_type: str) -> str:
        mapping = {
            "breakfast": "早餐",
            "lunch": "午餐",
            "dinner": "晚餐",
            "snack": "加餐",
        }
        return mapping.get(meal_type, meal_type)

    def generate_medication_message(
        self,
        drug_info: Optional[dict[str, Any]],
        custom_dose: Optional[str] = None,
    ) -> str:
        if not drug_info:
            return "请记得服用您的药物。"

        dose = custom_dose or drug_info.get("dosage", {}).get("initial", "")
        templates = drug_info.get("reminder_templates", {})
        template = (
            templates.get("fixed_time_cn")
            or templates.get("after_meal_cn")
            or templates.get("before_meal_cn")
            or "请记得服用 {drug} {dose}。"
        )
        return template.format(
            dose=dose,
            drug=drug_info.get("drug_name_cn", drug_info.get("drug_name_en", "未命名药物")),
        )

    def schedule_medication_task(
        self,
        *,
        drug_query: str,
        user_id: str,
        custom_dose: Optional[str] = None,
        scheduled_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Optional[Reminder]:
        drug_info = self.drug_knowledge.get_drug_info(drug_query)
        if not drug_info:
            return None

        reminder = self._create_and_enqueue(
            user_id=user_id,
            reminder_type=ReminderType.MEDICATION,
            message=self.generate_medication_message(drug_info, custom_dose),
            scheduled_at=scheduled_at,
            correlation_id=correlation_id,
            channel=channel,
            payload={
                "drug_query": drug_query,
                "drug_name": drug_info.get("drug_name_cn", drug_query),
                "timing_logic": drug_info.get("timing", {}).get("relation_to_meal_cn", ""),
                "safety_note": drug_info.get("special_notes", ""),
                "custom_dose": custom_dose or "",
            },
        )
        return reminder

    def check_threshold_and_wake(
        self,
        *,
        user_id: str,
        metric_type: MetricType | str,
        value: float,
        measured_at: Optional[str] = None,
        source: str = "manual",
        custom_rule: Optional[ThresholdRule] = None,
        raw_payload: Optional[dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Optional[Reminder]:
        metric_enum = metric_type if isinstance(metric_type, MetricType) else MetricType(metric_type)
        rule = custom_rule or DEFAULT_THRESHOLD_RULES.get(metric_enum)
        measured_at = measured_at or utc_now_iso()

        if not rule:
            return None

        reading = MetricReading.create(
            user_id=user_id,
            metric_type=metric_enum,
            metric_value=value,
            unit=rule.unit,
            measured_at=measured_at,
            source=source,
            raw_payload=raw_payload,
        )
        self.metric_repo.log_metric_reading(reading)

        exceed_reason = rule.evaluate(value)
        if not exceed_reason:
            return None

        metric_cn = self._metric_label_cn(metric_enum)
        message = (
            f"⚠️ {rule.alert_title}：当前{metric_cn}为 {value}{rule.unit}，{exceed_reason}。"
            "请尽快复测；如持续异常，请联系医生或照护者。"
        )

        return self._create_and_enqueue(
            user_id=user_id,
            reminder_type=ReminderType.THRESHOLD_ALERT,
            message=message,
            scheduled_at=measured_at,
            correlation_id=correlation_id,
            channel=channel,
            payload={
                "metric_type": metric_enum.value,
                "metric_value": value,
                "unit": rule.unit,
                "threshold_min": rule.min_value,
                "threshold_max": rule.max_value,
                "trigger_reason": exceed_reason,
                "source": source,
            },
        )

    def schedule_measurement_reminder(
        self,
        *,
        user_id: str,
        metric_type: MetricType | str,
        scheduled_at: Optional[str] = None,
        note: Optional[str] = None,
        correlation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Reminder:
        metric_enum = metric_type if isinstance(metric_type, MetricType) else MetricType(metric_type)
        metric_cn = self._metric_label_cn(metric_enum)
        message = f"请进行{metric_cn}测量，并记录结果。"
        if note:
            message += f" 备注：{note}"

        return self._create_and_enqueue(
            user_id=user_id,
            reminder_type=ReminderType.MEASUREMENT,
            message=message,
            scheduled_at=scheduled_at,
            correlation_id=correlation_id,
            channel=channel,
            payload={
                "metric_type": metric_enum.value,
                "note": note or "",
            },
        )

    def ensure_measurement_reminder_if_missing(
        self,
        *,
        user_id: str,
        metric_type: MetricType | str,
        max_gap_hours: int,
        scheduled_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Optional[Reminder]:
        metric_enum = metric_type if isinstance(metric_type, MetricType) else MetricType(metric_type)
        last_reading = self.metric_repo.get_last_metric_reading(user_id, metric_enum.value)
        now = datetime.now(timezone.utc)

        if not last_reading:
            return self.schedule_measurement_reminder(
                user_id=user_id,
                metric_type=metric_enum,
                scheduled_at=scheduled_at,
                note=f"最近 {max_gap_hours} 小时内没有测量记录",
                correlation_id=correlation_id,
                channel=channel,
            )

        last_ts = datetime.fromisoformat(last_reading["measured_at"])
        gap_hours = (now - last_ts).total_seconds() / 3600.0
        if gap_hours >= max_gap_hours:
            return self.schedule_measurement_reminder(
                user_id=user_id,
                metric_type=metric_enum,
                scheduled_at=scheduled_at,
                note=f"距离上次测量已 {gap_hours:.1f} 小时",
                correlation_id=correlation_id,
                channel=channel,
            )
        return None

    def record_food_intake(
        self,
        *,
        user_id: str,
        meal_type: str,
        foods: list[str],
        note: Optional[str] = None,
        recorded_at: Optional[str] = None,
    ) -> None:
        record = FoodRecord.create(
            user_id=user_id,
            meal_type=meal_type,
            foods=foods,
            note=note,
            recorded_at=recorded_at,
        )
        self.food_repo.log_food_record(record)

    def schedule_food_record_reminder(
        self,
        *,
        user_id: str,
        meal_type: str,
        scheduled_at: Optional[str] = None,
        call_agent_name: str = "饮食记录agent",
        correlation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Reminder:
        meal_cn = self._meal_label_cn(meal_type)
        message = f"请记录本次{meal_cn}饮食内容；如需分析，可调用 {call_agent_name}。"

        return self._create_and_enqueue(
            user_id=user_id,
            reminder_type=ReminderType.FOOD_RECORD,
            message=message,
            scheduled_at=scheduled_at,
            correlation_id=correlation_id,
            channel=channel,
            payload={
                "meal_type": meal_type,
                "call_agent": call_agent_name,
            },
        )

    def ensure_food_record_reminder_if_missing(
        self,
        *,
        user_id: str,
        meal_type: str,
        max_gap_hours: int = 6,
        scheduled_at: Optional[str] = None,
        correlation_id: Optional[str] = None,
        channel: Optional[str] = None,
    ) -> Optional[Reminder]:
        last_record = self.food_repo.get_latest_food_record(user_id, meal_type)
        now = datetime.now(timezone.utc)

        if not last_record:
            return self.schedule_food_record_reminder(
                user_id=user_id,
                meal_type=meal_type,
                scheduled_at=scheduled_at,
                correlation_id=correlation_id,
                channel=channel,
            )

        last_ts = datetime.fromisoformat(last_record["recorded_at"])
        gap_hours = (now - last_ts).total_seconds() / 3600.0
        if gap_hours >= max_gap_hours:
            return self.schedule_food_record_reminder(
                user_id=user_id,
                meal_type=meal_type,
                scheduled_at=scheduled_at,
                correlation_id=correlation_id,
                channel=channel,
            )
        return None

    def intercept_food_risk(
        self,
        *,
        food_input: str,
        user_meds: list[str],
    ) -> Optional[dict[str, str]]:
        if not food_input:
            return None

        food_norm = food_input.lower().strip()
        for med in user_meds:
            drug_info = self.drug_knowledge.get_drug_info(med)
            if not drug_info:
                continue

            interactions = drug_info.get("food_interactions", [])
            for interaction in interactions:
                interaction_norm = interaction.lower().strip()

                if food_norm in interaction_norm or interaction_norm in food_norm:
                    return {
                        "type": "RISK_BLOCK",
                        "warning": f"⚠️ 警告: 您正在服用 {drug_info.get('drug_name_cn', med)}。",
                        "detail": interaction,
                    }

                matches = difflib.get_close_matches(food_norm, [interaction_norm], n=1, cutoff=0.6)
                if matches:
                    return {
                        "type": "RISK_BLOCK_FUZZY",
                        "warning": f"⚠️ 警告 (可能相关): 您正在服用 {drug_info.get('drug_name_cn', med)}。",
                        "detail": f"查出疑似禁忌食物: {interaction} (与输入 '{food_input}' 高度相似)",
                    }
        return None

    def confirm_task(self, *, reminder_id: str, is_taken: bool) -> bool:
        return self.confirm_medication_intake(reminder_id=reminder_id, is_taken=is_taken)

    def confirm_medication_intake(self, *, reminder_id: str, is_taken: bool) -> bool:
        now_str = utc_now_iso()
        self.reminder_repo.log_confirmation(reminder_id, is_taken, now_str)
        new_state = ReminderState.ACKED if is_taken else ReminderState.IGNORED
        self.reminder_repo.update_state(reminder_id, new_state)
        return True

    def dispatch_due_events(
        self,
        *,
        now: Optional[str] = None,
        limit: int = 50,
    ) -> list[ReminderDispatchResult]:
        dispatch_time = now or utc_now_iso()
        events = self.outbox_repo.fetch_due_events(dispatch_time, limit)
        results: list[ReminderDispatchResult] = []

        for event in events:
            result = self.delivery.send(event)
            if result.success:
                self.outbox_repo.mark_sent(event.event_id, result.provider_msg_id)
                self.reminder_repo.update_state(event.reminder_id, ReminderState.SENT)
            else:
                self.outbox_repo.mark_failed(event.event_id, result.error or "unknown error")
                self.reminder_repo.update_state(event.reminder_id, ReminderState.FAILED)
            results.append(result)

        return results