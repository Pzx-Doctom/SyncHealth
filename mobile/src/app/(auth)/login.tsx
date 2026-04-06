/**
 * 登录页面 — 邮箱 + 密码登录
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

export default function LoginScreen() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const { login, isLoading, error, clearError } = useAuthStore();

  const handleLogin = async () => {
    if (!email.trim()) {
      Alert.alert('提示', '请输入邮箱');
      return;
    }
    if (!password.trim()) {
      Alert.alert('提示', '请输入密码');
      return;
    }

    try {
      await login(email.trim(), password);
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
        <Text className="text-white/70 text-base mt-2">Health Data Sync</Text>
      </LinearGradient>

      <View className="flex-1 -mt-8 bg-white rounded-t-3xl px-8 pt-8">
        <ScrollView
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
        >
          <Text className="text-text-primary text-2xl font-bold mb-2">
            欢迎回来
          </Text>
          <Text className="text-text-secondary text-base mb-6">
            登录以同步您的健康数据
          </Text>

          {error && (
            <View className="bg-red-50 border border-danger/20 rounded-xl px-4 py-3 mb-4">
              <Text className="text-danger text-sm">{error}</Text>
            </View>
          )}

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
            placeholder="请输入密码"
            value={password}
            onChangeText={(text) => {
              setPassword(text);
              clearError();
            }}
            secureTextEntry
          />

          <Pressable
            onPress={handleLogin}
            disabled={isLoading}
            className={`mt-4 h-14 rounded-xl items-center justify-center ${
              isLoading ? 'bg-primary/60' : 'bg-primary'
            }`}
          >
            {isLoading ? (
              <Text className="text-white text-base font-semibold">登录中...</Text>
            ) : (
              <Text className="text-white text-base font-semibold">登 录</Text>
            )}
          </Pressable>

          <View className="flex-row justify-center mt-8">
            <Text className="text-text-secondary text-sm">还没有账号？</Text>
            <Pressable onPress={() => router.push('/(auth)/register')}>
              <Text className="text-primary text-sm font-semibold ml-1">
                立即注册
              </Text>
            </Pressable>
          </View>
        </ScrollView>
      </View>
    </KeyboardAvoidingView>
  );
}
