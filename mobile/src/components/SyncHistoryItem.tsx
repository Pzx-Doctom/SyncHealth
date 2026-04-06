/**
 * 同步历史列表项组件
 * 显示：时间、状态徽章、统计数据
 */
import React from 'react';
import { View, Text } from 'react-native';
import type { SyncLogResponse } from '@/types/sync';
import { formatRelativeTime } from '@/utils/dateUtils';

interface SyncHistoryItemProps {
  item: SyncLogResponse;
}

const STATUS_BADGE = {
  completed: { label: '成功', bg: 'bg-green-100', text: 'text-success' },
  failed: { label: '失败', bg: 'bg-red-100', text: 'text-danger' },
  processing: { label: '处理中', bg: 'bg-yellow-100', text: 'text-warning' },
  pending: { label: '等待中', bg: 'bg-gray-100', text: 'text-text-secondary' },
} as const;

export function SyncHistoryItem({ item }: SyncHistoryItemProps) {
  const badge = STATUS_BADGE[item.status as keyof typeof STATUS_BADGE]
    || STATUS_BADGE.pending;

  return (
    <View className="bg-white rounded-xl px-4 py-3.5 mb-2 shadow-sm border border-gray-50">
      {/* 上行：时间 + 状态 */}
      <View className="flex-row items-center justify-between mb-2">
        <Text className="text-text-primary text-sm font-medium">
          {formatRelativeTime(item.started_at)}
        </Text>
        <View className={`px-2.5 py-0.5 rounded-full ${badge.bg}`}>
          <Text className={`text-xs font-semibold ${badge.text}`}>
            {badge.label}
          </Text>
        </View>
      </View>

      {/* 下行：数据统计 */}
      <View className="flex-row gap-4">
        <Text className="text-text-secondary text-xs">
          收到 <Text className="text-text-primary font-semibold">{item.records_received}</Text>
        </Text>
        <Text className="text-text-secondary text-xs">
          插入 <Text className="text-success font-semibold">{item.records_inserted}</Text>
        </Text>
        <Text className="text-text-secondary text-xs">
          去重 <Text className="text-text-tertiary font-semibold">{item.records_deduplicated}</Text>
        </Text>
      </View>

      {/* 错误信息 */}
      {item.error_message && (
        <Text className="text-danger text-xs mt-2">{item.error_message}</Text>
      )}
    </View>
  );
}
