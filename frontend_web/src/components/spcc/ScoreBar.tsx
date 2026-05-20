import { SPCC_COLORS } from '@/constants/spccColors';

interface Props {
  label: string;
  score: number; // 1..5
  alert?: boolean;
}

export function ScoreBar({ label, score, alert = false }: Props) {
  const pct = Math.max(0, Math.min(5, score)) / 5;
  const barColor = alert
    ? SPCC_COLORS.red.main
    : score >= 4
      ? SPCC_COLORS.green.main
      : score >= 3
        ? SPCC_COLORS.amber.main
        : SPCC_COLORS.red.main;

  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="w-24 shrink-0 text-muted-foreground">{label}</span>
      <div
        className="relative flex-1 h-3 rounded-full overflow-hidden"
        style={{ background: SPCC_COLORS.gray.light }}
      >
        <div
          className="absolute inset-y-0 left-0 rounded-full transition-all"
          style={{ width: `${pct * 100}%`, background: barColor }}
        />
      </div>
      <span className="w-10 shrink-0 text-right font-mono tabular-nums">
        {score}/5
      </span>
    </div>
  );
}
