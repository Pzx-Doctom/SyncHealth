/**
 * 注册页面 — 昵称 + 邮箱 + 密码注册
 */
import React, { useState } from 'react';
import {
  View,
  Text,
  Pressable,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  Alert,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { router } from 'expo-router';
import { FormInput } from '@/components/FormInput';
import { useAuthStore } from '@/stores/authStore';

export default function RegisterScreen() {
  const [displayName, setDisplayName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { register, isLoading, error, clearError } = useAuthStore();

  const handleRegister = async () => {
    if (!displayName.trim()) {
      Alert.alert('提示', '请输入昵称');
      return;
    }
    if (!email.trim()) {
      Alert.alert('提示', '请输入邮箱');
      return;
    }
    if (password.length < 6) {
      Alert.alert('提示', '密码至少 6 位');
      return;
    }

    try {
      await register(email.trim(), password, displayName.trim());
    } catch {
      // 错误已在 store 中处理
    }
  };

  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      className="flex-1 bg-bg-secondary"
    >
      <LinearGradient
        colors={['#667eea', '#764ba2']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        className="h-[35%] items-center justify-center"
      >
        <Text className="text-white text-3xl font-bold tracking-tight">SyncHealth</Text>
        <Text className="text-white/70 text-base mt-2">创建您的账户</Text>
      </LinearGradient>

      <View className="flex-1 -mt-8 bg-white rounded-t-3xl px-8 pt-8">
        <ScrollView
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <Text className="text-text-primary text-2xl font-bold mb-2">
            注册账户
          </Text>
          <Text className="text-text-secondary text-base mb-6">
            开始同步您的健康数据
          </Text>

          {error && (
            <View className="bg-red-50 border border-danger/20 rounded-xl px-4 py-3 mb-4">
              <Text className="text-danger text-sm">{error}</Text>
            </View>
          )}

          <FormInput
            placeholder="请输入昵称"
            value={displayName}
            onChangeText={(text) => {
              setDisplayName(text);
              clearError();
            }}
          />

          <FormInput
            placeholder="请输入邮箱"
            value={email}
            onChangeText={(text) => {
              setEmail(text);
              clearError();
            }}
            keyboardType="email-address"
            autoCapitalize="none"
          />

          <FormInput
            placeholder="请输入密码（至少 6 位）"
            value={password}
            onChangeText={(text) => {
              setPassword(text);
              clearError();
            }}
            secureTextEntry
          />

          <Pressable
            onPress={handleRegister}
            disabled={isLoading}
            className={`mt-4 h-14 rounded-xl items-center justify-center ${
              isLoading ? 'bg-primary/60' : 'bg-primary'
            }`}
          >
            {isLoading ? (
              <Text className="text-white text-base font-semibold">注册中...</Text>
            ) : (
              <Text className="text-white text-base font-semibold">注 册</Text>
            )}
          </Pressable>

          <View className="flex-row justify-center mt-8">
            <Text className="text-text-secondary text-sm">已有账号？</Text>
            <Pressable onPress={() => router.push('/(auth)/login')}>
              <Text className="text-primary text-sm font-semibold ml-1">
                立即登录
              </Text>
            </Pressable>
          </View>
        </ScrollView>
      </View>
    </KeyboardAvoidingView>
  );
}
