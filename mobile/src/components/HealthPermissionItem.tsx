/**
 * HealthKit 权限状态行组件
 * 显示：数据类型名称 + 授权状态指示器
 */
import React from 'react';
import { View, Text } from 'react-native';

interface HealthPermissionItemProps {
  label: string;
  status: 'authorized' | 'denied' | 'notDetermined';
}

const STATUS_CONFIG = {
  authorized: { icon: '✓', color: 'text-success', bg: 'bg-green-50' },
  denied: { icon: '✕', color: 'text-danger', bg: 'bg-red-50' },
  notDetermined: { icon: '?', color: 'text-warning', bg: 'bg-yellow-50' },
} as const;

export function HealthPermissionItem({ label, status }: HealthPermissionItemProps) {
  const config = STATUS_CONFIG[status];

  return (
    <View className="flex-row items-center justify-between py-3 border-b border-separator last:border-b-0">
      <Text className="text-text-primary text-sm">{label}</Text>
      <View className={`flex-row items-center px-2.5 py-1 rounded-full ${config.bg}`}>
        <Text className={`text-xs font-semibold ${config.color} mr-1`}>
          {config.icon}
        </Text>
        <Text className={`text-xs ${config.color}`}>
          {status === 'authorized' ? '已授权' : status === 'denied' ? '已拒绝' : '未确定'}
        </Text>
      </View>
    </View>
  );
}
