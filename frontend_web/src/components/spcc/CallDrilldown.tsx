import { useMemo, useState } from 'react';
import { AlertTriangle, ChevronRight, Search } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Checkbox } from '@/components/ui/checkbox';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useCallDetail, useCalls } from '@/api/spcc/hooks';
import { SPCC_COLORS } from '@/constants/spccColors';
import { EmotionTimelineChart } from './EmotionTimelineChart';
import { LLMEvalCard } from './LLMEvalCard';
import type { CallSummary, PeakUtterance } from '@/api/spcc/types';

interface Props {
  sessionId: string | null;
}

export function CallDrilldown({ sessionId }: Props) {
  const [query, setQuery] = useState('');
  const [flagOnly, setFlagOnly] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);

  const calls = useCalls(sessionId, { flagOnly, limit: 500 });
  const detail = useCallDetail(sessionId, selected);

  const filtered = useMemo(() => {
    if (!calls.data) return [];
    if (!query.trim()) return calls.data;
    const q = query.toLowerCase();
    return calls.data.filter(
      c =>
        c.call_id.toLowerCase().includes(q) ||
        c.operator.toLowerCase().includes(q) ||
        c.skill.toLowerCase().includes(q)
    );
  }, [calls.data, query]);

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
    <div className="grid gap-4 lg:grid-cols-[420px_1fr]">
      <Card className="h-fit">
        <CardHeader className="pb-3">
          <CardTitle className="text-base">通話を検索</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="relative">
            <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              className="pl-8"
              placeholder="通話ID / オペレーター / 種別"
              value={query}
              onChange={e => setQuery(e.target.value)}
            />
          </div>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <Checkbox
              checked={flagOnly}
              onCheckedChange={v => setFlagOnly(Boolean(v))}
            />
            要注意のみ表示
          </label>

          <ScrollArea className="h-[640px] -mx-3">
            <ul className="divide-y">
              {filtered.map(c => (
                <CallRow
                  key={c.call_id}
                  call={c}
                  selected={c.call_id === selected}
                  onClick={() => setSelected(c.call_id)}
                />
              ))}
              {filtered.length === 0 && (
                <li className="text-sm text-muted-foreground p-4">
                  該当する通話がありません
                </li>
              )}
            </ul>
          </ScrollArea>
        </CardContent>
      </Card>

      <div className="space-y-4">
        {!selected && (
          <Card className="border-dashed">
            <CardContent className="p-8 text-center text-sm text-muted-foreground">
              左の一覧から通話を選択してください。
            </CardContent>
          </Card>
        )}

        {selected && detail.isLoading && (
          <Card>
            <CardContent className="p-6 text-sm text-muted-foreground">
              通話詳細を取得中…（LLM評価を含むため数秒〜数十秒かかります）
            </CardContent>
          </Card>
        )}

        {detail.data && (
          <>
            <Card>
              <CardHeader>
                <CardTitle className="text-base">
                  {detail.data.call_id}
                </CardTitle>
                <div className="text-xs text-muted-foreground">
                  {detail.data.operator} / {detail.data.skill} /{' '}
                  {(detail.data.duration_sec / 60).toFixed(1)}分 /{' '}
                  {detail.data.direction === 'I'
                    ? 'インバウンド'
                    : detail.data.direction === 'O'
                      ? 'アウトバウンド'
                      : detail.data.direction}
                </div>
              </CardHeader>
              <CardContent>
                <EmotionTimelineChart data={detail.data.emotion_timeline} />
              </CardContent>
            </Card>

            {detail.data.peak_utterances.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <AlertTriangle className="h-4 w-4 text-red-600" />
                    不満ピーク発言（不満スコア ≥ 5）
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2">
                  {detail.data.peak_utterances.map((u, i) => (
                    <PeakRow key={i} utterance={u} />
                  ))}
                </CardContent>
              </Card>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="text-base">会話全文</CardTitle>
              </CardHeader>
              <CardContent>
                <TranscriptView
                  text={detail.data.transcript}
                  peaks={detail.data.peak_utterances}
                />
              </CardContent>
            </Card>

            <LLMEvalCard
              result={detail.data.llm_eval}
              loading={false}
              title="LLM 評価レポート"
            />
          </>
        )}
      </div>
    </div>
  );
}

function CallRow({
  call,
  selected,
  onClick,
}: {
  call: CallSummary;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <li>
      <button
        type="button"
        onClick={onClick}
        className={`w-full px-3 py-2 text-left hover:bg-muted/40 flex items-start gap-2 ${
          selected ? 'bg-muted/60' : ''
        }`}
      >
        <div className="flex-1 min-w-0">
          <div className="text-xs font-mono text-muted-foreground truncate">
            {call.call_id.slice(0, 12)}…
          </div>
          <div className="text-sm font-medium truncate">{call.operator}</div>
          <div className="text-xs text-muted-foreground truncate">
            {call.skill} / {(call.duration_sec / 60).toFixed(1)}分
          </div>
        </div>
        <div className="text-right shrink-0">
          <div className="text-xs tabular-nums">
            CUスコア {call.avg_agent_score.toFixed(2)}
          </div>
          {call.flagged ? (
            <span
              className="inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium"
              style={{
                background: SPCC_COLORS.red.light,
                color: SPCC_COLORS.red.text,
              }}
            >
              ⚠ 要注意
            </span>
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground inline" />
          )}
        </div>
      </button>
    </li>
  );
}

function PeakRow({ utterance }: { utterance: PeakUtterance }) {
  return (
    <div
      className="rounded-md p-3 text-sm"
      style={{
        background: SPCC_COLORS.red.light,
        borderLeft: `3px solid ${SPCC_COLORS.red.main}`,
      }}
    >
      <div className="text-xs text-muted-foreground mb-1 flex items-center gap-2">
        {utterance.timestamp && <span>⏱ {utterance.timestamp}</span>}
        <span>不満 {utterance.dissatisfied.toFixed(1)}</span>
        <span>怒り {utterance.anger.toFixed(1)}</span>
      </div>
      <div>{utterance.text}</div>
    </div>
  );
}

function TranscriptView({
  text,
  peaks,
}: {
  text: string;
  peaks: PeakUtterance[];
}) {
  const peakTexts = new Set(peaks.map(p => p.text.trim()));
  const lines = text
    .split(/\r?\n/)
    .map(l => l.trim())
    .filter(Boolean);

  return (
    <ScrollArea className="h-[420px]">
      <div className="space-y-1 text-sm font-mono pr-2">
        {lines.map((line, i) => {
          const isCu = line.startsWith('C:');
          const isOp = line.startsWith('O:');
          const body = line.replace(/^[CO]:\s*/, '');
          const isPeak = peakTexts.has(body);
          const color = isCu
            ? SPCC_COLORS.blue.text
            : isOp
              ? SPCC_COLORS.green.text
              : SPCC_COLORS.gray.text;
          return (
            <div
              key={i}
              className="px-2 py-1 rounded"
              style={
                isPeak
                  ? {
                      background: SPCC_COLORS.red.light,
                      borderLeft: `3px solid ${SPCC_COLORS.red.main}`,
                    }
                  : undefined
              }
            >
              <span className="font-semibold" style={{ color }}>
                {isCu ? 'C: ' : isOp ? 'O: ' : ''}
              </span>
              <span>{body || line}</span>
            </div>
          );
        })}
      </div>
    </ScrollArea>
  );
}
