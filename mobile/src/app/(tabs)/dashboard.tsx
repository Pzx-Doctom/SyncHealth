/**
 * 主仪表盘页面 — 同步状态 + 手动同步 + 同步历史
 */
import React, { useEffect } from 'react';
import { View, Text, Pressable, FlatList, RefreshControl, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { useSyncStore } from '@/stores/syncStore';
import { SyncStatusCard } from '@/components/SyncStatusCard';
import { SyncHistoryItem } from '@/components/SyncHistoryItem';

export default function DashboardScreen() {
  const {
    syncStatus,
    syncHistory,
    triggerManualSync,
    fetchSyncHistory,
    fetchSyncStatus,
  } = useSyncStore();

  // 页面加载时获取历史和状态
  useEffect(() => {
    fetchSyncHistory();
    fetchSyncStatus();
  }, []);

  // 同步成功后刷新
  useEffect(() => {
    if (syncStatus === 'success') {
      fetchSyncHistory();
    }
  }, [syncStatus]);

  const isSyncing = syncStatus === 'syncing';

  return (
    <View className="flex-1 bg-bg-secondary">
      {/* 顶部导航栏右侧按钮 */}
      <View className="absolute top-2 right-4 z-10">
        <Pressable
          onPress={() => router.push('/(tabs)/settings')}
          className="w-10 h-10 items-center justify-center rounded-full bg-white/80"
          hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
        >
          <Text className="text-lg">⚙️</Text>
        </Pressable>
      </View>

      <FlatList
        contentContainerStyle={{ padding: 20, paddingBottom: 40 }}
        data={syncHistory}
        keyExtractor={(item) => String(item.id)}
        showsVerticalScrollIndicator={false}
        ListHeaderComponent={
          <>
            {/* 同步状态卡片 */}
            <SyncStatusCard />

            {/* 手动同步按钮 */}
            <LinearGradient
              colors={isSyncing ? ['#8E8E93', '#AEAEB2'] : ['#4F46E5', '#667eea']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              className="rounded-2xl h-14 items-center justify-center mb-8 shadow-md"
            >
              <Pressable
                onPress={() => triggerManualSync()}
                disabled={isSyncing}
                className="w-full h-full items-center justify-center"
              >
                <Text className="text-white text-lg font-semibold">
                  {isSyncing ? '同步中...' : '↓ 手动同步'}
                </Text>
              </Pressable>
            </LinearGradient>

            {/* 历史标题 */}
            {syncHistory.length > 0 && (
              <View className="mb-3">
                <Text className="text-text-primary text-lg font-bold">
                  同步历史
                </Text>
                <Text className="text-text-secondary text-sm">
                  最近 {syncHistory.length} 次同步记录
                </Text>
              </View>
            )}
          </>
        }
        renderItem={({ item }) => (
          <SyncHistoryItem item={item} />
        )}
        ListEmptyComponent={
          <View className="items-center py-12">
            <Text className="text-4xl mb-3">📭</Text>
            <Text className="text-text-secondary text-base">
              暂无同步记录
            </Text>
            <Text className="text-text-tertiary text-sm mt-1">
              点击上方按钮开始第一次同步
            </Text>
          </View>
        }
        refreshControl={
          <RefreshControl
            refreshing={isSyncing}
            onRefresh={() => triggerManualSync()}
            tintColor="#4F46E5"
          />
        }
      />
    </View>
  );
}
