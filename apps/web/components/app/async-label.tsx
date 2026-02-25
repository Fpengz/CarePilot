export function AsyncLabel({
  active,
  idle,
  loading,
}: {
  active: boolean;
  idle: string;
  loading: string;
}) {
  return <>{active ? `${loading}\u2026` : idle}</>;
}
