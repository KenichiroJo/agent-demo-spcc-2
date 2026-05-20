import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { EMOTION_LINE_COLORS } from '@/constants/spccColors';
import type { EmotionPoint } from '@/api/spcc/types';

interface Props {
  data: EmotionPoint[];
  height?: number;
}

export function EmotionTimelineChart({ data, height = 240 }: Props) {
  if (data.length === 0) {
    return (
      <div className="text-sm text-muted-foreground py-8 text-center">
        感情データがありません
      </div>
    );
  }
  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="section" />
        <YAxis domain={[0, 10]} />
        <Tooltip />
        <Legend />
        <Line
          type="monotone"
          dataKey="agent_score"
          name="エージェントスコア (CU)"
          stroke={EMOTION_LINE_COLORS.cu_agent_score}
          strokeWidth={2}
          dot={{ r: 4 }}
        />
        <Line
          type="monotone"
          dataKey="positive"
          name="ポジティブ"
          stroke={EMOTION_LINE_COLORS.cu_positive}
          strokeWidth={2}
        />
        <Line
          type="monotone"
          dataKey="dissatisfied"
          name="不満"
          stroke={EMOTION_LINE_COLORS.cu_dissatisfied}
          strokeWidth={2}
          strokeDasharray="5 4"
        />
        <Line
          type="monotone"
          dataKey="anger"
          name="怒り"
          stroke={EMOTION_LINE_COLORS.cu_anger}
          strokeWidth={2}
          strokeDasharray="2 3"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
