/**
 * 设置页面 — 服务器地址 + 账号信息 + HealthKit 权限 + 登出
 */
import React, { useEffect, useState } from 'react';
import { View, Text, Pressable, ScrollView, Alert, Platform } from 'react-native';
import { useAuthStore } from '@/stores/authStore';
import { useSyncStore } from '@/stores/syncStore';
import { HealthPermissionItem } from '@/components/HealthPermissionItem';
import { getServerUrl, setServerUrl } from '@/services/apiClient';
import { HEALTH_DATA_GROUPS } from '@/constants/healthDataTypes';

export default function SettingsScreen() {
  const { user, logout } = useAuthStore();
  const { healthPermissions, fetchHealthPermissions, requestHealthPermissions } = useSyncStore();
  const [serverUrl, setServerUrlLocal] = useState('');
  const [isEditingServer, setIsEditingServer] = useState(false);

  useEffect(() => {
    loadServerUrl();
    fetchHealthPermissions();
  }, []);

  const loadServerUrl = async () => {
    const url = await getServerUrl();
    setServerUrlLocal(url);
  };

  const handleSaveServerUrl = async () => {
    await setServerUrl(serverUrl.trim());
    setIsEditingServer(false);
    Alert.alert('已保存', '服务器地址已更新');
  };

  const handleLogout = () => {
    Alert.alert('退出登录', '确定要退出登录吗？', [
      { text: '取消', style: 'cancel' },
      {
        text: '退出',
        style: 'destructive',
        onPress: () => logout(),
      },
    ]);
  };

  const handleRequestPermissions = async () => {
    if (Platform.OS === 'android') {
      Alert.alert('提示', 'Android 端使用模拟数据，无需请求 HealthKit 权限');
      return;
    }
    const granted = await requestHealthPermissions();
    if (granted) {
      Alert.alert('成功', '健康数据权限已授权');
    } else {
      Alert.alert('提示', '部分权限被拒绝，请在系统设置中手动开启');
    }
  };

  return (
    <ScrollView className="flex-1 bg-bg-secondary" showsVerticalScrollIndicator={false}>
      {/* 用户信息卡片 */}
      <View className="bg-white mx-5 mt-5 rounded-2xl p-5 shadow-sm">
        <View className="flex-row items-center">
          {/* 头像占位 */}
          <View className="w-14 h-14 rounded-full bg-primary/10 items-center justify-center mr-4">
            <Text className="text-primary text-xl font-bold">
              {user?.display_name?.charAt(0)?.toUpperCase() || '?'}
            </Text>
          </View>
          <View className="flex-1">
            <Text className="text-text-primary text-lg font-semibold">
              {user?.display_name || '未登录'}
            </Text>
            <Text className="text-text-secondary text-sm mt-0.5">
              {user?.email || '--'}
            </Text>
            {user?.created_at && (
              <Text className="text-text-tertiary text-xs mt-0.5">
                注册于 {new Date(user.created_at).toLocaleDateString('zh-CN')}
              </Text>
            )}
          </View>
        </View>
      </View>

      {/* 服务器地址配置 */}
      <View className="bg-white mx-5 mt-5 rounded-2xl overflow-hidden shadow-sm">
        <View className="px-5 pt-4 pb-2">
          <Text className="text-text-primary text-base font-semibold">
            服务器设置
          </Text>
          <Text className="text-text-tertiary text-xs mt-0.5">
            配置后端 API 地址（需与手机同一网络）
          </Text>
        </View>
        <View className="px-5 pb-4 pt-2">
          <View className="bg-bg-secondary rounded-xl px-4 h-11 flex-row items-center">
            <Text className="text-text-secondary text-sm flex-1 mr-2">
              {serverUrl}
            </Text>
            <Pressable
              onPress={() => setIsEditingServer(!isEditingServer)}
              className="text-primary"
              hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
            >
              <Text className="text-primary text-sm font-medium">
                {isEditingServer ? '取消' : '修改'}
              </Text>
            </Pressable>
          </View>
          {isEditingServer && (
            <View className="mt-3">
              <View className="bg-bg-secondary rounded-xl px-4 h-11 items-center justify-center">
                <Text className="text-text-tertiary text-sm">点击修改按钮编辑地址</Text>
              </View>
              <Text className="text-text-tertiary text-xs mt-1.5">
                提示：使用电脑的局域网 IP（如 192.168.1.100:8000/api/v1）
              </Text>
            </View>
          )}
        </View>
      </View>

      {/* HealthKit 权限状态 */}
      <View className="bg-white mx-5 mt-5 rounded-2xl overflow-hidden shadow-sm">
        <View className="px-5 pt-4 pb-1 flex-row items-center justify-between">
          <View>
            <Text className="text-text-primary text-base font-semibold">
              数据权限
            </Text>
            <Text className="text-text-tertiary text-xs mt-0.5">
              HealthKit 健康数据访问权限
            </Text>
          </View>
          <Pressable
            onPress={handleRequestPermissions}
            className="bg-primary/10 px-3 py-1.5 rounded-lg"
          >
            <Text className="text-primary text-xs font-semibold">授权</Text>
          </Pressable>
        </View>
        <View className="px-5 pb-2">
          {healthPermissions.map((perm) => (
            <HealthPermissionItem
              key={perm.key}
              label={perm.label}
              status={perm.status as 'authorized' | 'denied' | 'notDetermined'}
            />
          ))}
        </View>
      </View>

      {/* 退出登录 */}
      <Pressable
        onPress={handleLogout}
        className="mx-5 mt-8 mb-4 h-12 bg-white items-center justify-center rounded-2xl shadow-sm border border-danger/10"
      >
        <Text className="text-danger text-base font-semibold">退出登录</Text>
      </Pressable>

      {/* 版本号 */}
      <Text className="text-text-tertiary text-xs text-center mb-10">
        SyncHealth Mobile v1.0.0
      </Text>
    </ScrollView>
  );
}
