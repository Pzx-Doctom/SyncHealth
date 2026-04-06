/**
 * 平台判断和设备信息获取工具
 */
import { Platform } from 'react-native';
import * as Device from 'expo-device';

/** 当前是否为 iOS */
export const isIOS = Platform.OS === 'ios';

/** 当前是否为 Android */
export const isAndroid = Platform.OS === 'android';

/** 获取设备信息（用于 SyncPayload.device_info） */
export function getDeviceInfo() {
  return {
    model: Device.modelName || Device.deviceName || 'Unknown',
    os_version: `${Platform.OS} ${Platform.Version}`,
    app_version: '1.0.0',
  };
}
