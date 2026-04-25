import type {
  Reporter,
  TestCase,
  TestResult,
  FullResult,
} from '@playwright/test/reporter';
import fs from 'fs';
import path from 'path';

/**
 * Markdown 報告 reporter
 *
 * 每次跑完測試在 e2e/reports/ 下產出兩份：
 *   - latest.md（永遠是最新一次）
 *   - e2e-{timestamp}.md（歷史快照）
 *
 * 報告依「測試組」分區，組別對應在 GROUPS 設定，新增第 N 組時補一條
 * { match: ..., name: '第N組: ...' }。
 */

interface TestEntry {
  group: string;
  project: string;
  file: string;
  title: string;
  status: TestResult['status'];
  duration: number;
  error?: string;
}

const GROUPS: Array<{ match: RegExp; name: string }> = [
  // 第1組: Dashboard / Profile / Account（純展示、權限基線）
  { match: /tests\/auth\//, name: '第1組: Dashboard / Profile / Account' },
  { match: /tests\/admin\//, name: '第1組: Dashboard / Profile / Account' },
  { match: /tests\/employee\//, name: '第1組: Dashboard / Profile / Account' },
  { match: /tests\/teacher-portal\//, name: '第1組: Dashboard / Profile / Account' },
  { match: /tests\/student-portal\//, name: '第1組: Dashboard / Profile / Account' },

  // 後續組別（檔案還沒長出來，但先佔位）
  { match: /tests\/group2-employees-roles\//, name: '第2組: Employees + Role 權限' },
  { match: /tests\/group3-people\//, name: '第3組: Teacher / Student 人員建立' },
  { match: /tests\/group4-course-contract\//, name: '第4組: Course + Teacher Contract' },
  { match: /tests\/group5-zoom\//, name: '第5組: Zoom Accounts' },
  { match: /tests\/group6-prereqs\//, name: '第6組: 選課 / 時段 / 偏好' },
  { match: /tests\/group7-student-contract\//, name: '第7組: Student Contract' },
  { match: /tests\/group8-booking\//, name: '第8組: Booking 預約管理' },
  { match: /tests\/group9-booking-overview\//, name: '第9組: Booking Overview' },
  { match: /tests\/group10-leave\//, name: '第10組: Leave / 代課' },
  { match: /tests\/group11-bonus\//, name: '第11組: Teacher Bonus' },
  { match: /tests\/group12-trial-to-formal\//, name: '第12組: 試上轉正' },
  { match: /tests\/group13-portal\//, name: '第13組: Portal 檢視' },

  { match: /tests\/cross-role\//, name: '跨角色整合' },
  { match: /tests\/permissions\//, name: '權限矩陣' },
];

function classifyGroup(filePath: string): string {
  const normalized = filePath.replace(/\\/g, '/');
  for (const g of GROUPS) {
    if (g.match.test(normalized)) return g.name;
  }
  return '未分類';
}

function trimError(msg: string | undefined): string | undefined {
  if (!msg) return undefined;
  // 去除 ANSI escape sequences + 取前幾行精華
  const stripped = msg.replace(/\x1b\[[0-9;]*m/g, '');
  return stripped.split('\n').slice(0, 3).join(' ').trim().slice(0, 280);
}

function statusIcon(s: TestResult['status']): string {
  if (s === 'passed') return '✓';
  if (s === 'failed' || s === 'timedOut') return '✗';
  if (s === 'skipped') return '○';
  return '?';
}

export default class MarkdownReporter implements Reporter {
  private entries: TestEntry[] = [];
  private startedAt = Date.now();

  onBegin(): void {
    this.startedAt = Date.now();
  }

  onTestEnd(test: TestCase, result: TestResult): void {
    // retry 會多次觸發 onTestEnd；用 testId + retry 替換掉舊 entry，保留最後一次嘗試的狀態
    const file = test.location.file;
    const entry: TestEntry = {
      group: classifyGroup(file),
      project: test.parent.project()?.name ?? '',
      file: path.relative(process.cwd(), file),
      title: test.titlePath().slice(3).join(' › '),
      status: result.status,
      duration: result.duration,
      error: trimError(result.error?.message),
    };
    const idx = this.entries.findIndex(
      (e) => e.file === entry.file && e.title === entry.title && e.project === entry.project
    );
    if (idx >= 0) this.entries[idx] = entry;
    else this.entries.push(entry);
  }

  async onEnd(_result: FullResult): Promise<void> {
    const duration = Date.now() - this.startedAt;
    const md = this.render(duration);

    const reportsDir = path.resolve(__dirname, '..', 'reports');
    fs.mkdirSync(reportsDir, { recursive: true });

    const stamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
    fs.writeFileSync(path.join(reportsDir, 'latest.md'), md);
    fs.writeFileSync(path.join(reportsDir, `e2e-${stamp}.md`), md);

    console.log(`\n📄 Markdown report: e2e/reports/latest.md  (snapshot: e2e-${stamp}.md)`);
  }

  private render(durationMs: number): string {
    const total = this.entries.length;
    const pass = this.entries.filter((e) => e.status === 'passed').length;
    const fail = this.entries.filter((e) => e.status === 'failed' || e.status === 'timedOut').length;
    const skip = this.entries.filter((e) => e.status === 'skipped').length;

    const overall = fail === 0 ? '🟢 全部通過' : `🔴 ${fail} 個失敗`;
    const lines: string[] = [];

    lines.push(`# EOP E2E 測試報告`);
    lines.push('');
    lines.push(`- **執行時間**: ${new Date().toISOString()}`);
    lines.push(`- **狀態**: ${overall}`);
    lines.push(`- **總計**: ${pass} / ${total} 通過（失敗 ${fail}，跳過 ${skip}）`);
    lines.push(`- **耗時**: ${(durationMs / 1000).toFixed(1)}s`);
    lines.push('');

    // 依組分組
    const groups = new Map<string, TestEntry[]>();
    for (const e of this.entries) {
      if (!groups.has(e.group)) groups.set(e.group, []);
      groups.get(e.group)!.push(e);
    }

    // 排序：以 GROUPS 順序為主，未分類墊底
    const groupOrder = [...GROUPS.map((g) => g.name), '跨角色整合', '權限矩陣', '未分類'];
    const sortedGroups = [...groups.entries()].sort(
      (a, b) => groupOrder.indexOf(a[0]) - groupOrder.indexOf(b[0])
    );

    lines.push(`## 各組結果`);
    lines.push('');

    for (const [groupName, entries] of sortedGroups) {
      const gPass = entries.filter((e) => e.status === 'passed').length;
      const gFail = entries.filter((e) => e.status === 'failed' || e.status === 'timedOut').length;
      const gIcon = gFail === 0 ? '🟢' : '🔴';

      lines.push(`### ${gIcon} ${groupName}`);
      lines.push('');
      lines.push(`通過 **${gPass} / ${entries.length}**　·　耗時 ${(entries.reduce((a, e) => a + e.duration, 0) / 1000).toFixed(1)}s`);
      lines.push('');

      // 細表
      lines.push(`| Project | Spec | 結果 | 耗時 |`);
      lines.push(`|---------|------|------|------|`);
      for (const e of entries) {
        const fileBase = path.basename(e.file);
        const icon = statusIcon(e.status);
        lines.push(`| \`${e.project}\` | \`${fileBase}\` › ${e.title} | ${icon} ${e.status} | ${(e.duration / 1000).toFixed(2)}s |`);
      }
      lines.push('');

      // 失敗詳情
      const fails = entries.filter((e) => e.status === 'failed' || e.status === 'timedOut');
      if (fails.length > 0) {
        lines.push(`**失敗詳情**`);
        lines.push('');
        for (const f of fails) {
          lines.push(`- **${f.title}** (\`${f.file}\`, project \`${f.project}\`)`);
          if (f.error) {
            lines.push(`  > ${f.error}`);
          }
        }
        lines.push('');
      }
    }

    lines.push(`---`);
    lines.push('');
    lines.push(`> 由 \`e2e/reporters/markdown.ts\` 自動產生。新增測試組時請同步擴充 \`GROUPS\` 對應規則。`);

    return lines.join('\n');
  }
}
