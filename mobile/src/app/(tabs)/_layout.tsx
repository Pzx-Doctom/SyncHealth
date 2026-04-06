/**
 * 主页标签栏布局 — Dashboard + Settings 底部 Tab 导航
 */
import React from 'react';
import { Tabs } from 'expo-router';
import { Text, View } from 'react-native';

export default function TabsLayout() {
  return (
    <Tabs
      screenOptions={{
        headerShown: true,
        headerTitleAlign: 'center',
        headerShadowVisible: false,
        headerBackgroundColor: '#FFFFFF',
        headerTitleStyle: {
          fontFamily: 'System',
          fontWeight: '700',
          fontSize: 18,
          color: '#1C1C1E',
        },
        tabBarActiveTintColor: '#4F46E5',
        tabBarInactiveTintColor: '#8E8E93',
        tabBarBackgroundColor: '#FFFFFF',
        tabBarStyle: {
          borderTopWidth: 0.5,
          borderTopColor: '#E5E5EA',
          paddingTop: 4,
          paddingBottom: 20,
        },
        tabBarLabelStyle: {
          fontFamily: 'System',
          fontSize: 11,
          fontWeight: '500',
        },
      }}
    >
      <Tabs.Screen
        name="dashboard"
        options={{
          title: 'SyncHealth',
          headerRight: () => null,
          tabBarLabel: '首页',
          tabBarIcon: ({ color, size }) => (
            <View className="items-center justify-center">
              <Text style={{ fontSize: size, color }}>📊</Text>
            </View>
          ),
        }}
      />
      <Tabs.Screen
        name="settings"
        options={{
          title: '设置',
          tabBarLabel: '设置',
          tabBarIcon: ({ color, size }) => (
            <View className="items-center justify-center">
              <Text style={{ fontSize: size, color }}>⚙️</Text>
            </View>
          ),
        }}
      />
    </Tabs>
  );
}
