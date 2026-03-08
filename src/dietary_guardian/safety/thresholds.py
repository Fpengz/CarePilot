"""
Clinical threshold constants used by safety checks.

References:
- Singapore Health Promotion Board (HPB) public nutrition guidance:
  sodium intake target is 2,000mg/day or less for adults.
- The sugar warning fraction remains conservative at 30% of daily limit
  for single-meal alerting until a stricter clinical policy is adopted.
"""

SODIUM_WARNING_FRACTION = 0.5
SUGAR_WARNING_FRACTION = 0.3
