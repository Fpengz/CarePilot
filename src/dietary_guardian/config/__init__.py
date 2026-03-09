"""Public configuration exports for the application bootstrap layer."""

from dietary_guardian.config.app import AppSettings, get_settings
from dietary_guardian.config.llm import LLMCapability, LLMCapabilityTarget, LLMSettings, LocalModelProfile, ModelProvider
from dietary_guardian.config.runtime import AppConfig, LocalModelSettings, MedicalConfig, ModelSettings

Settings = AppSettings

__all__ = [
    "AppSettings",
    "AppConfig",
    "MedicalConfig",
    "ModelSettings",
    "LocalModelProfile",
    "LocalModelSettings",
    "LLMSettings",
    "LLMCapability",
    "LLMCapabilityTarget",
    "ModelProvider",
    "Settings",
    "get_settings",
]
