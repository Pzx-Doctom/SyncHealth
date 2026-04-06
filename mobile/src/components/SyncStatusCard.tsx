/**
 * 同步状态卡片组件 — Dashboard 页面的核心视觉元素
 * 显示：同步状态指示器、状态文字、上次同步详情
 */
import React from 'react';
import { View, Text } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Animated, { useSharedValue, useAnimatedProps, withRepeat, withTiming, Easing } from 'react-native-reanimated';
import Svg, { Circle } from 'react-native-svg';
import { useSyncStore } from '@/stores/syncStore';
import { formatRelativeTime } from '@/utils/dateUtils';

const AnimatedCircle = Animated.createAnimatedComponent(Circle);

/** 同步状态配置 */
const STATUS_CONFIG = {
  idle: { label: '等待同步', color: '#8E8E93', icon: '○' },
  syncing: { label: '正在同步...', color: '#4F46E5', icon: '◎' },
  success: { label: '同步成功', color: '#34C759', icon: '●' },
  error: { label: '同步失败', color: '#FF3B30', icon: '✕' },
} as const;

export function SyncStatusCard() {
  const { syncStatus, lastSyncResult, syncError, lastSyncAt } = useSyncStore();
  const config = STATUS_CONFIG[syncStatus];

  // 旋转动画（同步中）
  const rotation = useSharedValue(0);
  if (syncStatus === 'syncing') {
    rotation.value = 0;
  }
  const animatedRotation = useAnimatedProps(() => ({
    rotation: syncStatus === 'syncing'
      ? withRepeat(withTiming(360, { duration: 1500, easing: Easing.linear }), -1)
      : 0,
  }));

  return (
    <LinearGradient
      colors={['#4F46E5', '#667eea']}
      start={{ x: 0, y: 0 }}
      end={{ x: 1, y: 1 }}
      className="rounded-2xl p-6 mb-6 shadow-lg"
    >
      {/* 状态指示器 */}
      <View className="items-center mb-4">
        <View className="w-20 h-20 rounded-full bg-white/20 items-center justify-center">
          {syncStatus === 'syncing' ? (
            <Svg width="40" height="40" viewBox="0 0 40 40">
              <AnimatedCircle
                cx="20"
                cy="20"
                r="16"
                stroke="white"
                strokeWidth="3"
                fill="none"
                strokeDasharray="75 25"
                strokeLinecap="round"
                animatedProps={animatedRotation}
              />
            </Svg>
          ) : (
            <Text className="text-white text-3xl">{config.icon}</Text>
          )}
        </View>
        <Text className="text-white text-lg font-semibold mt-3">
          {config.label}
        </Text>
        {lastSyncAt && (
          <Text className="text-white/70 text-sm mt-1">
            上次同步：{formatRelativeTime(lastSyncAt)}
          </Text>
        )}
      </View>

      {/* 错误信息 */}
      {syncError && (
        <View className="bg-white/15 rounded-lg px-4 py-2 mb-4">
          <Text className="text-white text-sm text-center">{syncError}</Text>
        </View>
      )}

      {/* 同步详情 */}
      {lastSyncResult && (
        <View className="flex-row justify-around bg-white/10 rounded-xl py-3">
          <View className="items-center">
            <Text className="text-white font-bold text-lg">
              {lastSyncResult.records_received}
            </Text>
            <Text className="text-white/60 text-xs mt-0.5">收到</Text>
          </View>
          <View className="w-px bg-white/20" />
          <View className="items-center">
            <Text className="text-white font-bold text-lg">
              {lastSyncResult.records_inserted}
            </Text>
            <Text className="text-white/60 text-xs mt-0.5">插入</Text>
          </View>
          <View className="w-px bg-white/20" />
          <View className="items-center">
            <Text className="text-white font-bold text-lg">
              {lastSyncResult.records_deduplicated}
            </Text>
            <Text className="text-white/60 text-xs mt-0.5">去重</Text>
          </View>
        </View>
      )}
    </LinearGradient>
  );
}
