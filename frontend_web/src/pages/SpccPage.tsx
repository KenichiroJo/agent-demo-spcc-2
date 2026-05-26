import { useState } from 'react';
import {
  Activity,
  BarChart3,
  Headphones,
  HelpCircle,
  Users,
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { UploadAndDashboard } from '@/components/spcc/UploadAndDashboard';
import { OperatorReport } from '@/components/spcc/OperatorReport';
import { CallDrilldown } from '@/components/spcc/CallDrilldown';
import {
  TUTORIAL_STORAGE_KEY,
  TutorialOverlay,
} from '@/components/spcc/TutorialOverlay';

const STORAGE_KEY = 'spcc_session_id';

export default function SpccPage() {
  const [sessionId, setSessionId] = useState<string | null>(() => {
    try {
      return sessionStorage.getItem(STORAGE_KEY);
    } catch {
      return null;
    }
  });
  const [tutorialOpen, setTutorialOpen] = useState<boolean>(() => {
    try {
      return localStorage.getItem(TUTORIAL_STORAGE_KEY) !== '1';
    } catch {
      return false;
    }
  });

  const handleSession = (id: string) => {
    setSessionId(id);
    try {
      sessionStorage.setItem(STORAGE_KEY, id);
    } catch {
      /* ignore */
    }
  };

  const handleReset = () => {
    setSessionId(null);
    try {
      sessionStorage.removeItem(STORAGE_KEY);
    } catch {
      /* ignore */
    }
  };

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b bg-card sticky top-0 z-10">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="rounded-md bg-primary/10 p-2">
              <Headphones className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h1 className="text-lg font-semibold">SPCC 感情カルテ</h1>
              <p className="text-xs text-muted-foreground">
                コールセンター通話の LLM 自動評価ダッシュボード
              </p>
            </div>
          </div>
          <div className="flex items-center gap-3 text-xs text-muted-foreground">
            <span className="hidden md:inline">
              DataRobot LLM Gateway 経由で評価
            </span>
            <button
              type="button"
              onClick={() => setTutorialOpen(true)}
              className="flex items-center gap-1 text-primary hover:underline"
              title="使い方を表示"
            >
              <HelpCircle className="h-4 w-4" />
              使い方
            </button>
            {sessionId && (
              <button
                type="button"
                onClick={handleReset}
                className="text-primary hover:underline"
              >
                セッションをリセット
              </button>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-6">
        <Tabs defaultValue="dashboard" className="w-full">
          <TabsList>
            <TabsTrigger value="dashboard" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              ダッシュボード
            </TabsTrigger>
            <TabsTrigger value="operators" className="gap-2">
              <Users className="h-4 w-4" />
              オペレーター別
            </TabsTrigger>
            <TabsTrigger value="calls" className="gap-2">
              <Activity className="h-4 w-4" />
              通話ドリルダウン
            </TabsTrigger>
          </TabsList>

          <TabsContent value="dashboard">
            <UploadAndDashboard
              sessionId={sessionId}
              onSessionCreated={handleSession}
            />
          </TabsContent>
          <TabsContent value="operators">
            <OperatorReport sessionId={sessionId} />
          </TabsContent>
          <TabsContent value="calls">
            <CallDrilldown sessionId={sessionId} />
          </TabsContent>
        </Tabs>
      </main>

      <TutorialOverlay
        open={tutorialOpen}
        onClose={() => setTutorialOpen(false)}
      />
    </div>
  );
}
