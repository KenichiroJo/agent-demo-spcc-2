import { useState } from 'react';
import {
  Activity,
  BarChart3,
  FileText,
  Headphones,
  UploadCloud,
  Users,
  type LucideIcon,
} from 'lucide-react';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { SPCC_COLORS } from '@/constants/spccColors';

export const TUTORIAL_STORAGE_KEY = 'spcc_tutorial_seen';

interface TutorialStep {
  icon: LucideIcon;
  title: string;
  body: string;
  tone: keyof typeof SPCC_COLORS;
}

const STEPS: TutorialStep[] = [
  {
    icon: Headphones,
    tone: 'purple',
    title: 'SPCC 感情カルテへようこそ',
    body: 'コールセンター通話を LLM で自動評価するデモアプリです。3 つのタブで「全体 → オペレーター → 個別通話」と順にドリルダウンできます。最初に CSV をアップロードして分析を開始しましょう。',
  },
  {
    icon: UploadCloud,
    tone: 'teal',
    title: 'Step 1: CSV を 2 つアップロード',
    body: '「通話単位 CSV (utf-8-sig)」と「発話単位 CSV (cp932)」を選んで「分析開始」ボタンを押します。\n\nお手元にデータがない場合は、サーバー側で `fastapi_server/scripts/generate_dummy_csv.py` を実行するとサンプル CSV が生成できます。',
  },
  {
    icon: BarChart3,
    tone: 'green',
    title: 'Step 2: ダッシュボードで全体把握',
    body: 'アップロードが完了すると、通話数 / 平均通話時間 / 要注意通話数 / オペレーター数の KPI、問合せ種別 TOP 5、エージェントスコア分布が表示されます。\n\n「要注意」は CU 不満スコアが 5 以上のピーク発言を含む通話です。',
  },
  {
    icon: Users,
    tone: 'amber',
    title: 'Step 3: オペレーター別レポート',
    body: '「オペレーター別」タブでプルダウンから担当者を選択すると、担当件数・平均通話時間・問合せ種別の円グラフ、そして代表通話に対する LLM 評価サマリ (S/A/B/C グレード・改善点・コーチング提案) が出ます。\n\n代表通話は「最も不満スコアが高かった通話」が自動選択されます。',
  },
  {
    icon: Activity,
    tone: 'red',
    title: 'Step 4: 通話ドリルダウン',
    body: '「通話ドリルダウン」タブで通話を 1 件選ぶと、感情推移グラフ (前半 / 中盤 / 後半) ・不満スコア 5 以上のピーク発言 (赤ハイライト) ・会話全文・5 項目スコアの完全な LLM レポートが見られます。\n\n左の検索ボックスで通話 ID / オペレーター名 / 種別から絞り込めます。',
  },
  {
    icon: FileText,
    tone: 'gray',
    title: 'データ仕様 (補足)',
    body: '通話単位 CSV: encoding=utf-8-sig、必須カラム = key, userName, skill, duration, direction, latest\n\n発話単位 CSV: encoding=cp932、必須カラム = 通話ID, 音声のチャンネル種類, 発言内容(最新版数), CUの怒り/不満/ポジティブ/エージェントスコア\n\n結合キー: 通話単位の `key` ↔ 発話単位の `通話ID` (一致率 50% 未満で 400 エラー)',
  },
];

interface Props {
  open: boolean;
  onClose: () => void;
}

export function TutorialOverlay({ open, onClose }: Props) {
  const [stepIdx, setStepIdx] = useState(0);
  const step = STEPS[stepIdx];
  const isFirst = stepIdx === 0;
  const isLast = stepIdx === STEPS.length - 1;

  const handleClose = () => {
    try {
      localStorage.setItem(TUTORIAL_STORAGE_KEY, '1');
    } catch {
      /* ignore */
    }
    setStepIdx(0);
    onClose();
  };

  const Icon = step.icon;
  const tone = SPCC_COLORS[step.tone];

  return (
    <Dialog open={open} onOpenChange={o => !o && handleClose()}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <div
              className="rounded-full p-3 shrink-0"
              style={{ background: tone.light, color: tone.text }}
            >
              <Icon className="h-5 w-5" />
            </div>
            <DialogTitle className="text-base sm:text-lg">
              {step.title}
            </DialogTitle>
          </div>
          <div className="mt-3 flex items-center gap-2">
            {STEPS.map((_, i) => (
              <span
                key={i}
                className="h-1.5 flex-1 rounded-full transition-all"
                style={{
                  background:
                    i === stepIdx
                      ? tone.main
                      : i < stepIdx
                        ? tone.light
                        : 'var(--muted)',
                }}
                aria-hidden
              />
            ))}
          </div>
          <div className="text-xs text-muted-foreground mt-2">
            {stepIdx + 1} / {STEPS.length}
          </div>
        </DialogHeader>

        <div className="text-sm leading-relaxed py-4 whitespace-pre-line">
          {step.body}
        </div>

        <DialogFooter className="flex justify-between gap-2 sm:justify-between">
          <Button variant="ghost" onClick={handleClose} type="button">
            スキップ
          </Button>
          <div className="flex gap-2">
            <Button
              variant="outline"
              type="button"
              disabled={isFirst}
              onClick={() => setStepIdx(i => i - 1)}
            >
              戻る
            </Button>
            {isLast ? (
              <Button type="button" onClick={handleClose}>
                始める
              </Button>
            ) : (
              <Button type="button" onClick={() => setStepIdx(i => i + 1)}>
                次へ
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
