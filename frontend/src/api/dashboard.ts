import apiClient from './client'
import type { DashboardSummary, DashboardTrends, HealthScore } from '../types/dashboard'

// =============================================
// 知识点：对象字面量 (Object Literal)
// ---------------------------------------------
// 对象字面量是指用 { key: value } 语法直接创建对象的方式，
// 与通过 class 实例化或 new Object() 不同，它是一种更简洁的声明方式。
// 下面的 dashboardApi 就是一个对象字面量，里面直接定义了 3 个方法。
// 等价写法对比：
//   对象字面量:    const obj = { name: 'hello', sayHi() {} }
//   class 写法:    class Obj { name = 'hello'; sayHi() {} }  const obj = new Obj()
// =============================================
export const dashboardApi = {
  // =============================================
  // 知识点：TypeScript 泛型 (Generics)
  // ---------------------------------------------
  // apiClient.get<DashboardSummary>(...) 中的 <DashboardSummary> 就是泛型语法。
  // 它的作用是告诉 axios：这个请求的响应数据 res.data 应该符合 DashboardSummary 的类型。
  // 好处：
  //   1. IDE 自动补全：输入 res.data. 时会提示 DashboardSummary 中定义的所有字段
  //   2. 类型检查：如果访问了不存在的字段，TypeScript 会报错提示
  // 对比：
  //   不用泛型:  apiClient.get('/dashboard/summary')       → res.data 类型为 any，无提示
  //   使用泛型:  apiClient.get<DashboardSummary>('/...')    → res.data 类型为 DashboardSummary，有完整提示
  // =============================================
  getSummary() {
    return apiClient.get<DashboardSummary>('/dashboard/summary')
  },
  getTrends(period: string = '7d') {
    // { params: { period } } 也是一个对象字面量，作为 axios 的第二个配置参数
    // 其中 { period } 是 ES6 的简写，等同于 { period: period }
    return apiClient.get<DashboardTrends>('/dashboard/trends', { params: { period } })
  },
  getHealthScore() {
    return apiClient.get<HealthScore>('/dashboard/health-score')
  },
}
