import { GRADE_COLORS } from '@/constants/spccColors';

interface Props {
  grade: 'S' | 'A' | 'B' | 'C' | null | undefined;
  size?: 'sm' | 'md' | 'lg';
}

export function GradeBadge({ grade, size = 'md' }: Props) {
  if (!grade) {
    return <span className="text-xs text-muted-foreground">—</span>;
  }
  const c = GRADE_COLORS[grade];
  const sizeClass =
    size === 'lg'
      ? 'h-12 w-12 text-2xl'
      : size === 'md'
        ? 'h-8 w-8 text-base'
        : 'h-6 w-6 text-xs';
  return (
    <span
      className={`inline-flex items-center justify-center rounded-full font-bold ${sizeClass}`}
      style={{ background: c.bg, color: c.text }}
    >
      {grade}
    </span>
  );
}
