import os
import re

# Mapping of old absolute module names to new absolute module names
absolute_mappings = {
    "care_pilot.platform.auth.auth_service": "care_pilot.platform.auth.auth_service",
    "care_pilot.features.medications.medication_management": "care_pilot.features.medications.medication_management",
    "care_pilot.features.recommendations.recommendation_engine": "care_pilot.features.recommendations.recommendation_engine",
    "care_pilot.features.recommendations.recommendation_service": "care_pilot.features.recommendations.recommendation_service",
    "care_pilot.features.safety.safety_engine": "care_pilot.features.safety.safety_engine",
    "care_pilot.features.safety.safety_service": "care_pilot.features.safety.safety_service",
    "care_pilot.features.households.household_service": "care_pilot.features.households.household_service",
    "care_pilot.features.meals.meal_service": "care_pilot.features.meals.meal_service",
    "care_pilot.features.symptoms.symptom_service": "care_pilot.features.symptoms.symptom_service",
    "care_pilot.features.profiles.profile_service": "care_pilot.features.profiles.profile_service",
    "care_pilot.features.reminders.outbox.outbox_service": "care_pilot.features.reminders.outbox.outbox_service",
    "care_pilot.features.reminders.reminder_service": "care_pilot.features.reminders.reminder_service",
    "care_pilot.features.reminders.notifications.notification_service": "care_pilot.features.reminders.notifications.notification_service",
    "care_pilot.features.reports.report_service": "care_pilot.features.reports.report_service",
    "care_pilot.features.reports.report_application_service": "care_pilot.features.reports.report_application_service",
    "care_pilot.features.companion.companion_orchestration": "care_pilot.features.companion.companion_orchestration",
    "care_pilot.features.companion.core.evidence.evidence_service": "care_pilot.features.companion.core.evidence.evidence_service",
    "care_pilot.features.companion.core.companion_core_service": "care_pilot.features.companion.core.companion_core_service",
    "care_pilot.features.companion.clinician_digest.clinical_cards.clinical_card_service": "care_pilot.features.companion.clinician_digest.clinical_cards.clinical_card_service",
    "care_pilot.features.companion.patient_card.patient_card_service": "care_pilot.features.companion.patient_card.patient_card_service",
    "care_pilot.features.companion.impact.metrics.impact_metric_service": "care_pilot.features.companion.impact.metrics.impact_metric_service",
}

# Mapping of directory to relative replacement
# Key: directory path
# Value: list of (old_relative, new_relative)
relative_mappings = {
    "src/care_pilot/platform/auth/": [("use_cases", "auth_service")],
    "src/care_pilot/features/medications/": [("use_cases", "medication_management")],
    "src/care_pilot/features/recommendations/": [("service", "recommendation_engine"), ("use_cases", "recommendation_service")],
    "src/care_pilot/features/safety/": [("service", "safety_engine"), ("use_cases", "safety_service")],
    "src/care_pilot/features/households/": [("use_cases", "household_service")],
    "src/care_pilot/features/meals/": [("service", "meal_service")],
    "src/care_pilot/features/symptoms/": [("use_cases", "symptom_service")],
    "src/care_pilot/features/profiles/": [("use_cases", "profile_service")],
    "src/care_pilot/features/reminders/outbox/": [("service", "outbox_service")],
    "src/care_pilot/features/reminders/": [("service", "reminder_service")],
    "src/care_pilot/features/reminders/notifications/": [("use_cases", "notification_service")],
    "src/care_pilot/features/reports/": [("service", "report_service"), ("use_cases", "report_application_service")],
    "src/care_pilot/features/companion/": [("service", "companion_orchestration")],
    "src/care_pilot/features/companion/core/evidence/": [("use_cases", "evidence_service")],
    "src/care_pilot/features/companion/core/": [("use_cases", "companion_core_service")],
    "src/care_pilot/features/companion/clinician_digest/clinical_cards/": [("use_cases", "clinical_card_service")],
    "src/care_pilot/features/companion/patient_card/": [("use_cases", "patient_card_service")],
    "src/care_pilot/features/companion/impact/metrics/": [("use_cases", "impact_metric_service")],
}

def update_file(file_path):
    with open(file_path, encoding='utf-8') as f:
        content = f.read()

    new_content = content

    # Apply absolute mappings
    for old, new in absolute_mappings.items():
        new_content = new_content.replace(old, new)

    # Apply relative mappings if file is in the specified directory
    for dir_path, mappings in relative_mappings.items():
        # Ensure dir_path is absolute for comparison if needed, but here relative to root is fine
        if file_path.startswith(dir_path):
            for old, new in mappings:
                # Common relative patterns
                new_content = re.sub(r'\bfrom \. import ' + old + r'\b', 'from . import ' + new, new_content)
                new_content = re.sub(r'\bfrom \.' + old + r' import\b', 'from .' + new + ' import', new_content)
                new_content = re.sub(r'\bimport ' + old + r'\b', 'import ' + new, new_content)
                new_content = re.sub(r'\bfrom ' + old + r' import\b', 'from ' + new + ' import', new_content)
                # Specially for households/__init__.py
                if "households/__init__.py" in file_path:
                    new_content = new_content.replace('from . import ' + old, 'from . import ' + new)
                    new_content = new_content.replace('return getattr(' + old, 'return getattr(' + new)

    # Also handle some loose patterns like docstrings mentioning the old file
    # Only if they match exactly as part of a path
    for old, new in absolute_mappings.items():
        # Replace file path in docstrings
        old_path = old.replace('.', '/') + ".py"
        new_path = new.replace('.', '/') + ".py"
        new_content = new_content.replace(old_path, new_path)

    if new_content != content:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        return True
    return False

def main():
    updated_files = []
    for root, dirs, files in os.walk('.'):
        if '.git' in dirs:
            dirs.remove('.git')
        if '.venv' in dirs:
            dirs.remove('.venv')
        if 'node_modules' in dirs:
            dirs.remove('node_modules')

        for file in files:
            if file.endswith(('.py', '.md')):
                file_path = os.path.join(root, file)
                # Normalize path
                if file_path.startswith('./'):
                    file_path = file_path[2:]
                if update_file(file_path):
                    updated_files.append(file_path)

    print(f"Updated {len(updated_files)} files:")
    for f in updated_files:
        print(f" - {f}")

if __name__ == "__main__":
    main()
