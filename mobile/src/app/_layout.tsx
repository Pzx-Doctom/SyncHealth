/**
 * 根布局 — Expo Router 入口
 * 负责认证守卫：根据 isAuthenticated 切换 Auth / Main 路由
 */
import React, { useEffect } from 'react';
import { Stack, useRouter, useSegments } from 'expo-router';
import { View, ActivityIndicator } from 'react-native';
import { useAuthStore } from '@/stores/authStore';

export default function RootLayout() {
  const { isAuthenticated, isLoading, checkAuth } = useAuthStore();
  const segments = useSegments();
  const router = useRouter();

  // 应用启动时检查认证状态
  useEffect(() => {
    checkAuth();
  }, []);

  // 认证状态变化时路由守卫
  useEffect(() => {
    if (isLoading) return;

    const inAuthGroup = segments[0] === '(auth)';

    if (!isAuthenticated && !inAuthGroup) {
      // 未登录 → 跳转登录页
      router.replace('/(auth)/login');
    } else if (isAuthenticated && inAuthGroup) {
      // 已登录 → 跳转主页
      router.replace('/(tabs)/dashboard');
    }
  }, [isAuthenticated, isLoading, segments]);

  // 加载中显示 loading
  if (isLoading) {
    return (
      <View className="flex-1 items-center justify-center bg-bg-secondary">
        <ActivityIndicator size="large" color="#4F46E5" />
      </View>
    );
  }

  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(auth)" />
      <Stack.Screen name="(tabs)" />
    </Stack>
  );
}
