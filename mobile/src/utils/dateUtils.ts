/**
 * 日期格式化工具
 */

/** ISO 8601 字符串 → "2026-04-05 14:30" 格式 */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return '暂无';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return '无效日期';

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/** ISO 8601 字符串 → "14:30" 格式 */
export function formatTime(isoString: string): string {
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return '--:--';

  const hours = String(date.getHours()).padStart(2, '0');
  const minutes = String(date.getMinutes()).padStart(2, '0');

  return `${hours}:${minutes}`;
}

/** ISO 8601 字符串 → "今天 14:30" / "昨天 09:15" / "4月5日" */
export function formatRelativeTime(isoString: string | null | undefined): string {
  if (!isoString) return '暂无';
  const date = new Date(isoString);
  if (isNaN(date.getTime())) return '无效日期';

  const now = new Date();
  const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  const yesterday = new Date(today.getTime() - 86400000);
  const target = new Date(date.getFullYear(), date.getMonth(), date.getDate());

  const timeStr = formatTime(isoString);

  if (target.getTime() === today.getTime()) return `今天 ${timeStr}`;
  if (target.getTime() === yesterday.getTime()) return `昨天 ${timeStr}`;

  return `${date.getMonth() + 1}月${date.getDate()}日 ${timeStr}`;
}

/** 获取 N 天前的 ISO 日期字符串（用于 sync_window.start） */
export function daysAgo(days: number): string {
  const date = new Date();
  date.setDate(date.getDate() - days);
  return date.toISOString();
}

/** 获取当前时间的 ISO 日期字符串（用于 sync_window.end） */
export function nowISO(): string {
  return new Date().toISOString();
}
