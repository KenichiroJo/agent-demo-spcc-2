import { AlertCircle, BookOpen, MessageSquare, Sparkles, ThumbsUp } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { GradeBadge } from './GradeBadge';
import { ScoreBar } from './ScoreBar';
import { SPCC_COLORS } from '@/constants/spccColors';
import type { LLMEvalResult } from '@/api/spcc/types';

interface Props {
  result: LLMEvalResult | null;
  loading?: boolean;
  title?: string;
}

const SCORE_LABELS: Array<[keyof NonNullable<LLMEvalResult['scores']>, string]> = [
  ['listening', '傾聴・共感'],
  ['problem_solving', '問題解決'],
  ['clarity', '説明明確さ'],
  ['manner', '言葉遣い'],
  ['efficiency', '通話効率'],
];

export function LLMEvalCard({ result, loading, title }: Props) {
  if (loading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Sparkles className="h-4 w-4" />
            {title ?? 'LLM 評価サマリ'}
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm text-muted-foreground">
          評価生成中…（数秒〜数十秒お待ちください）
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return null;
  }

  if (result.error) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2 text-red-700">
            <AlertCircle className="h-4 w-4" />
            LLM 評価エラー
          </CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p className="text-red-700">{result.error}</p>
          <p className="text-muted-foreground mt-2 text-xs">
            再試行する場合は、ページを再読込してください。
          </p>
        </CardContent>
      </Card>
    );
  }

  const total = result.total ?? 0;
  const totalOver100 = Math.round((total / 25) * 100);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Sparkles className="h-4 w-4" />
          {title ?? 'LLM 評価サマリ'}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center gap-4">
          <GradeBadge grade={result.grade} size="lg" />
          <div>
            <div className="text-3xl font-bold tabular-nums">
              {totalOver100}
              <span className="text-base text-muted-foreground">/100</span>
            </div>
            <div className="text-xs text-muted-foreground">
              {total}/25 ({result.grade ?? '—'})
            </div>
          </div>
        </div>

        {result.scores && (
          <div className="space-y-2">
            {SCORE_LABELS.map(([k, label]) => (
              <ScoreBar
                key={k}
                label={label}
                score={result.scores![k]}
                alert={result.scores![k] <= 2}
              />
            ))}
          </div>
        )}

        {result.summary && (
          <Section icon={<BookOpen className="h-4 w-4" />} label="📝 サマリ">
            <p className="text-sm leading-relaxed">{result.summary}</p>
          </Section>
        )}

        {result.highlights.length > 0 && (
          <Section
            icon={<ThumbsUp className="h-4 w-4" />}
            label="✓ 良かった点"
            tone="green"
          >
            <ul className="text-sm space-y-1 list-disc pl-5">
              {result.highlights.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </Section>
        )}

        {result.improvements.length > 0 && (
          <Section
            icon={<AlertCircle className="h-4 w-4" />}
            label="⚑ 改善点"
            tone="amber"
          >
            <ul className="text-sm space-y-1 list-disc pl-5">
              {result.improvements.map((h, i) => (
                <li key={i}>{h}</li>
              ))}
            </ul>
          </Section>
        )}

        {result.coaching && (
          <Section
            icon={<MessageSquare className="h-4 w-4" />}
            label="💬 コーチング提案"
            tone="purple"
          >
            <p className="text-sm leading-relaxed">{result.coaching}</p>
          </Section>
        )}

        {(result.peak_moment || result.resolution) && (
          <div className="grid gap-3 sm:grid-cols-2">
            {result.peak_moment && (
              <Section label="⚠ 不満ピーク" tone="red">
                <p className="text-xs leading-relaxed">{result.peak_moment}</p>
              </Section>
            )}
            {result.resolution && (
              <Section label="🔄 収束" tone="teal">
                <p className="text-xs leading-relaxed">{result.resolution}</p>
              </Section>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function Section({
  icon,
  label,
  tone = 'gray',
  children,
}: {
  icon?: React.ReactNode;
  label: string;
  tone?: keyof typeof SPCC_COLORS;
  children: React.ReactNode;
}) {
  const c = SPCC_COLORS[tone];
  return (
    <div
      className="rounded-md p-3"
      style={{ background: c.light, color: c.text }}
    >
      <div className="flex items-center gap-2 text-xs font-medium mb-1">
        {icon}
        {label}
      </div>
      <div className="text-foreground/90">{children}</div>
    </div>
  );
}
