import { ApiRequestError, isApiRequestError } from "./core";
import type { ApiErrorEnvelope } from "@/lib/types";

declare const envelope: ApiErrorEnvelope;
declare const unknownError: unknown;

const apiError = new ApiRequestError({
  status: 429,
  detail: "rate limited",
  envelope,
  requestId: "req-1",
  correlationId: "corr-1",
});

const typedCode: string | undefined = apiError.error.code;
const typedCorrelation: string | null = apiError.correlationId;

if (isApiRequestError(unknownError)) {
  const maybeRequestId: string | null = unknownError.requestId;
  const maybeDetail: string = unknownError.detail;
  const maybeEnvelope: ApiErrorEnvelope = unknownError.envelope;
  void maybeRequestId;
  void maybeDetail;
  void maybeEnvelope;
}

void typedCode;
void typedCorrelation;
