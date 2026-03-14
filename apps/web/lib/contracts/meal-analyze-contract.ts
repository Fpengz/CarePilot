import type { MealAnalyzeApiResponse } from "@/lib/types";

type HasKey<T, K extends PropertyKey> = K extends keyof T ? true : false;

type _ExpectValidatedEvent = HasKey<MealAnalyzeApiResponse, "validated_event">;
type _ExpectNutritionProfile = HasKey<MealAnalyzeApiResponse, "nutrition_profile">;
type _ExpectRawObservation = HasKey<MealAnalyzeApiResponse, "raw_observation">;
type _ExpectWorkflow = HasKey<MealAnalyzeApiResponse, "workflow">;
type _ExpectOutputEnvelope = HasKey<MealAnalyzeApiResponse, "output_envelope">;

const _assertValidatedEvent: _ExpectValidatedEvent = true;
const _assertNutritionProfile: _ExpectNutritionProfile = true;
const _assertRawObservation: _ExpectRawObservation = true;
const _assertWorkflow: _ExpectWorkflow = true;
const _assertOutputEnvelope: _ExpectOutputEnvelope = true;

export {};
