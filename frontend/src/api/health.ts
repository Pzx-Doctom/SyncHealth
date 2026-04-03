import apiClient from './client'
import type { PaginatedResponse, HeartRateOut, HRVSampleOut, ActivitySampleOut, SleepSessionOut, BloodOxygenSampleOut, BodyTemperatureSampleOut, WorkoutRecordOut, ECGRecordOut, RespiratoryRateSampleOut, NoiseExposureSampleOut, MindfulnessSessionOut } from '../types/health'

interface DateRangeParams {
  start?: string
  end?: string
  page?: number
  page_size?: number
}

export const healthApi = {
  getHeartRates(params: DateRangeParams & { measurement_type?: string } = {}) {
    return apiClient.get<PaginatedResponse<HeartRateOut>>('/health/heart-rate', { params })
  },
  getHRV(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<HRVSampleOut>>('/health/hrv', { params })
  },
  getActivity(params: DateRangeParams & { metric?: string } = {}) {
    return apiClient.get<PaginatedResponse<ActivitySampleOut>>('/health/activity', { params })
  },
  getSleep(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<SleepSessionOut>>('/health/sleep', { params })
  },
  getBloodOxygen(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<BloodOxygenSampleOut>>('/health/blood-oxygen', { params })
  },
  getBodyTemperature(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<BodyTemperatureSampleOut>>('/health/body-temperature', { params })
  },
  getWorkouts(params: DateRangeParams & { workout_type?: string } = {}) {
    return apiClient.get<PaginatedResponse<WorkoutRecordOut>>('/health/workouts', { params })
  },
  getECG(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<ECGRecordOut>>('/health/ecg', { params })
  },
  getRespiratoryRate(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<RespiratoryRateSampleOut>>('/health/respiratory-rate', { params })
  },
  getNoiseExposure(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<NoiseExposureSampleOut>>('/health/noise-exposure', { params })
  },
  getMindfulness(params: DateRangeParams = {}) {
    return apiClient.get<PaginatedResponse<MindfulnessSessionOut>>('/health/mindfulness', { params })
  },
}
