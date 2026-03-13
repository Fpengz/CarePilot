export type MessageKind =
  | "proactive_alert"
  | "meal_analysis"
  | "recommendation"
  | "follow_up"
  | "trend_insight"
  | "plain";

export type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  emotion?: { label: string; score: number };
  tag?: string;
  mealProposal?: { proposalId: string; mealText: string };
  title?: string;
  explanation?: string;
  reasoning?: string;
  confidence?: number;
};

export type MessageView = Message & {
  kind: MessageKind;
  title?: string;
  explanation?: string;
  reasoning?: string;
  confidence?: number;
};
