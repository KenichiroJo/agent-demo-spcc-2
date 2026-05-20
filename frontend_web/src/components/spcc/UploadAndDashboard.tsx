import { useState } from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { AlertTriangle, Database, Timer, Users, UploadCloud } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { useUploadFiles, useDashboard } from '@/api/spcc/hooks';
import { SPCC_COLORS } from '@/constants/spccColors';
import type { DashboardStats } from '@/api/spcc/types';

interface Props {
  sessionId: string | null;
  onSessionCreated: (id: string) => void;
}

function StatCard({
  icon,
  label,
  value,
  unit,
  tone,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  unit?: string;
  tone: keyof typeof SPCC_COLORS;
}) {
  const c = SPCC_COLORS[tone];
  return (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-center gap-3">
          <div
            className="flex h-10 w-10 items-center justify-center rounded-full"
            style={{ background: c.light, color: c.text }}
          >
            {icon}
          </div>
          <div>
            <div className="text-xs text-muted-foreground">{label}</div>
            <div className="text-2xl font-semibold tabular-nums">
              {value}
              {unit ? <span className="text-sm ml-1">{unit}</span> : null}
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function DashboardView({ stats }: { stats: DashboardStats }) {
  const skills = stats.skill_breakdown.slice(0, 5);
  const skillColors = [
    SPCC_COLORS.purple.main,
    SPCC_COLORS.green.main,
    SPCC_COLORS.teal.main,
    SPCC_COLORS.amber.main,
    SPCC_COLORS.gray.main,
  ];

  return (
    <div className="space-y-4">
      <div className="grid gap-4 grid-cols-2 md:grid-cols-4">
        <StatCard
          icon={<Database className="h-5 w-5" />}
          label="通話数"
          value={stats.total_calls.toLocaleString()}
          tone="purple"
        />
        <StatCard
          icon={<Timer className="h-5 w-5" />}
          label="平均通話時間"
          value={(stats.avg_duration_sec / 60).toFixed(1)}
          unit="分"
          tone="teal"
        />
        <StatCard
          icon={<AlertTriangle className="h-5 w-5" />}
          label="要注意通話"
          value={stats.alert_calls.toLocaleString()}
          tone="red"
        />
        <StatCard
          icon={<Users className="h-5 w-5" />}
          label="オペレーター数"
          value={stats.operator_count.toLocaleString()}
          tone="amber"
        />
      </div>

      <div className="grid gap-4 grid-cols-1 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">問合せ種別 TOP 5</CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={skills} layout="vertical" margin={{ left: 24 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis type="number" />
                <YAxis dataKey="skill" type="category" width={120} />
                <Tooltip />
                <Bar dataKey="count">
                  {skills.map((_, i) => (
                    <Cell key={i} fill={skillColors[i % skillColors.length]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              エージェントスコア分布（CU平均）
            </CardTitle>
          </CardHeader>
          <CardContent className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={stats.score_distribution}>
                <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill={SPCC_COLORS.green.main} />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      <div className="text-xs text-muted-foreground">
        結合キーの一致率: {(stats.match_rate * 100).toFixed(1)}%
      </div>
    </div>
  );
}

export function UploadAndDashboard({ sessionId, onSessionCreated }: Props) {
  const [callsFile, setCallsFile] = useState<File | null>(null);
  const [utterancesFile, setUtterancesFile] = useState<File | null>(null);
  const [progress, setProgress] = useState(0);
  const upload = useUploadFiles();
  const dashboard = useDashboard(sessionId);

  const handleSubmit = async () => {
    if (!callsFile || !utterancesFile) return;
    setProgress(0);
    try {
      const res = await upload.mutateAsync({
        calls: callsFile,
        utterances: utterancesFile,
        onProgress: setProgress,
      });
      onSessionCreated(res.session_id);
    } catch (e) {
      // surfaced via upload.error
      console.error(e);
    }
  };

  const errorMsg = upload.isError
    ? extractErrorMessage(upload.error)
    : null;

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <UploadCloud className="h-4 w-4" />
            CSV をアップロード
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-4 md:grid-cols-2">
            <FileInput
              label="通話単位CSV (utf-8-sig)"
              accept=".csv"
              file={callsFile}
              onChange={setCallsFile}
            />
            <FileInput
              label="発話単位CSV (cp932)"
              accept=".csv"
              file={utterancesFile}
              onChange={setUtterancesFile}
            />
          </div>
          <div className="flex items-center gap-3">
            <Button
              onClick={handleSubmit}
              disabled={!callsFile || !utterancesFile || upload.isPending}
            >
              {upload.isPending ? `アップロード中… ${progress}%` : '分析開始'}
            </Button>
            {errorMsg && (
              <span className="text-sm text-red-600">{errorMsg}</span>
            )}
          </div>
        </CardContent>
      </Card>

      {dashboard.isLoading && (
        <div className="text-sm text-muted-foreground">ダッシュボードを読込中…</div>
      )}
      {dashboard.data && <DashboardView stats={dashboard.data} />}
      {!sessionId && !upload.isPending && (
        <Card className="border-dashed">
          <CardContent className="p-8 text-center text-sm text-muted-foreground">
            2 つの CSV をアップロードすると、全体統計が表示されます。
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function FileInput({
  label,
  accept,
  file,
  onChange,
}: {
  label: string;
  accept: string;
  file: File | null;
  onChange: (f: File | null) => void;
}) {
  return (
    <label className="flex flex-col gap-2 rounded-md border border-dashed p-4 hover:bg-muted/30 cursor-pointer">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      <span className="text-sm truncate">
        {file ? file.name : '📁 ファイルを選択'}
      </span>
      <input
        type="file"
        accept={accept}
        className="hidden"
        onChange={e => onChange(e.target.files?.[0] ?? null)}
      />
    </label>
  );
}

function extractErrorMessage(err: unknown): string {
  if (!err) return '';
  if (typeof err === 'object' && err !== null && 'response' in err) {
    const resp = (err as { response?: { data?: { detail?: string } } }).response;
    if (resp?.data?.detail) return resp.data.detail;
  }
  if (err instanceof Error) return err.message;
  return String(err);
}
