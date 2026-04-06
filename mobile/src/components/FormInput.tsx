/**
 * 通用表单输入框组件
 * 支持：图标、密码显示切换、错误状态、焦点高亮
 */
import React, { useState } from 'react';
import { View, TextInput, Text, Pressable } from 'react-native';

interface FormInputProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChangeText: (text: string) => void;
  secureTextEntry?: boolean;
  error?: string | null;
  autoCapitalize?: 'none' | 'sentences' | 'words';
  autoCorrect?: boolean;
  keyboardType?: 'default' | 'email-address' | 'numeric' | 'phone-pad';
  editable?: boolean;
  leftIcon?: React.ReactNode;
}

export function FormInput({
  label,
  placeholder,
  value,
  onChangeText,
  secureTextEntry = false,
  error = null,
  autoCapitalize = 'none',
  autoCorrect = false,
  keyboardType = 'default',
  editable = true,
  leftIcon,
}: FormInputProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const borderColor = error
    ? 'border-danger'
    : isFocused
      ? 'border-primary'
      : 'border-transparent';

  return (
    <View className="mb-4">
      {label && (
        <Text className="text-text-secondary text-sm font-medium mb-1.5 ml-1">
          {label}
        </Text>
      )}
      <View
        className={`flex-row items-center bg-bg-secondary rounded-xl px-4 h-12 border-2 ${borderColor}`}
      >
        {leftIcon && <View className="mr-3 opacity-50">{leftIcon}</View>}
        <TextInput
          className="flex-1 text-text-primary text-base h-full"
          placeholder={placeholder}
          placeholderTextColor="#AEAEB2"
          value={value}
          onChangeText={onChangeText}
          secureTextEntry={secureTextEntry && !showPassword}
          autoCapitalize={autoCapitalize}
          autoCorrect={autoCorrect}
          keyboardType={keyboardType}
          editable={editable}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
        />
        {secureTextEntry && (
          <Pressable
            onPress={() => setShowPassword(!showPassword)}
            className="ml-2 px-1"
            hitSlop={{ top: 10, bottom: 10, left: 10, right: 10 }}
          >
            <Text className="text-primary text-sm font-medium">
              {showPassword ? '隐藏' : '显示'}
            </Text>
          </Pressable>
        )}
      </View>
      {error && (
        <Text className="text-danger text-xs mt-1 ml-1">{error}</Text>
      )}
    </View>
  );
}
