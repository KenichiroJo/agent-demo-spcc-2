import { useMemo, useState } from 'react';
import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { useOperatorReport, useOperators } from '@/api/spcc/hooks';
import { SPCC_COLORS } from '@/constants/spccColors';
import { LLMEvalCard } from './LLMEvalCard';

interface Props {
  sessionId: string | null;
}

const PIE_COLORS = [
  SPCC_COLORS.purple.main,
  SPCC_COLORS.green.main,
  SPCC_COLORS.teal.main,
  SPCC_COLORS.amber.main,
  SPCC_COLORS.gray.main,
  SPCC_COLORS.red.main,
];

export function OperatorReport({ sessionId }: Props) {
  const operators = useOperators(sessionId);
  const [selected, setSelected] = useState<string | null>(null);
  const report = useOperatorReport(sessionId, selected);

  const headerMetrics = useMemo(() => {
    if (!report.data) return null;
    const s = report.data.summary_stats;
    return [
      { label: '担当件数', value: `${s.calls_count}件` },
      { label: '平均通話時間', value: `${(s.avg_duration_sec / 60).toFixed(1)}分` },
      { label: '平均CUスコア', value: s.avg_agent_score.toFixed(2) },
      {
        label: '要注意率',
        value: `${(s.alert_rate * 100).toFixed(1)}%`,
      },
    ];
  }, [report.data]);

  if (!sessionId) {
    return (
      <Card className="border-dashed">
        <CardContent className="p-8 text-center text-sm text-muted-foreground">
          先にデータをアップロードしてください。
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader>
          <CardTitle className="text-base">オペレーターを選択</CardTitle>
        </CardHeader>
        <CardContent>
          <Select
            value={selected ?? ''}
            onValueChange={v => setSelected(v || null)}
          >
            <SelectTrigger className="w-full md:w-96">
              <SelectValue
                placeholder={
                  operators.isLoading
                    ? '読込中…'
                    : 'オペレーターを選択してください'
                }
              />
            </SelectTrigger>
            <SelectContent>
              {operators.data?.map(op => (
                <SelectItem key={op.name} value={op.name}>
                  {op.name} — {op.calls_count}件
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {selected && (
        <>
          {headerMetrics && (
            <Card>
              <CardContent className="p-4">
                <div className="text-lg font-semibold mb-2">{selected}</div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                  {headerMetrics.map(m => (
                    <div
                      key={m.label}
                      className="rounded-md border p-3"
                    >
                      <div className="text-xs text-muted-foreground">{m.label}</div>
                      <div className="text-xl font-semibold tabular-nums">
                        {m.value}
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">問合せ種別の内訳</CardTitle>
              </CardHeader>
              <CardContent className="h-64">
                {report.data && report.data.skill_breakdown.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Tooltip />
                      <Pie
                        data={report.data.skill_breakdown}
                        dataKey="count"
                        nameKey="skill"
                        cx="50%"
                        cy="50%"
                        outerRadius={80}
                        label={entry => `${entry.skill} (${entry.count})`}
                      >
                        {report.data.skill_breakdown.map((_, i) => (
                          <Cell
                            key={i}
                            fill={PIE_COLORS[i % PIE_COLORS.length]}
                          />
                        ))}
                      </Pie>
                    </PieChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="text-sm text-muted-foreground py-8 text-center">
                    データなし
                  </div>
                )}
              </CardContent>
            </Card>

            <LLMEvalCard
              result={report.data?.llm_eval_summary ?? null}
              loading={report.isLoading || report.isFetching}
              title={`LLM評価サマリ (代表通話${
                report.data?.representative_call_id
                  ? `: ${report.data.representative_call_id.slice(0, 8)}…`
                  : ''
              })`}
            />
          </div>

          {report.isError && (
            <Card>
              <CardContent className="text-sm text-red-700 p-4">
                オペレーターレポートの取得に失敗しました。
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  );
}
