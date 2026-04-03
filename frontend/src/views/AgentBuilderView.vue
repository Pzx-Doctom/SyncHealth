<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { agentApi } from '../api/ai'
import type { AgentOut, AgentCreate } from '../types/ai'

const agents = ref<AgentOut[]>([])
const loading = ref(false)
const showForm = ref(false)
const editingId = ref<number | null>(null)

const form = ref<AgentCreate>({
  name: '',
  description: '',
  system_prompt: '',
  health_data_scope: [],
})

const dataScopes = [
  'heart_rate', 'sleep', 'activity', 'blood_oxygen',
  'workout', 'temperature', 'respiratory_rate', 'mindfulness',
]

const scopeLabels: Record<string, string> = {
  heart_rate: '心率', sleep: '睡眠', activity: '活动', blood_oxygen: '血氧',
  workout: '运动', temperature: '体温', respiratory_rate: '呼吸', mindfulness: '正念',
}

onMounted(fetchAgents)

async function fetchAgents() {
  loading.value = true
  try {
    const res = await agentApi.list()
    agents.value = res.data
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  form.value = { name: '', description: '', system_prompt: '', health_data_scope: [] }
  showForm.value = true
}

function openEdit(agent: AgentOut) {
  editingId.value = agent.id
  form.value = {
    name: agent.name,
    description: agent.description || '',
    system_prompt: agent.system_prompt,
    health_data_scope: agent.health_data_scope || [],
  }
  showForm.value = true
}

async function saveAgent() {
  if (editingId.value) {
    await agentApi.update(editingId.value, form.value)
  } else {
    await agentApi.create(form.value)
  }
  showForm.value = false
  await fetchAgents()
}

async function deleteAgent(id: number) {
  if (confirm('确定删除该智能体？')) {
    await agentApi.delete(id)
    await fetchAgents()
  }
}

function toggleScope(scope: string) {
  const list = form.value.health_data_scope || []
  const idx = list.indexOf(scope)
  if (idx >= 0) list.splice(idx, 1)
  else list.push(scope)
  form.value.health_data_scope = [...list]
}
</script>

<template>
  <div>
    <div class="page-header" style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <h1>智能体管理</h1>
        <p>创建和管理基于健康数据的 AI 智能体</p>
      </div>
      <button class="btn btn-primary" @click="openCreate">+ 创建智能体</button>
    </div>

    <div v-if="loading" class="loading">加载中...</div>

    <!-- Agent List -->
    <div class="agents-grid" v-if="!showForm">
      <div v-if="agents.length === 0" class="empty card">
        <p>暂无智能体，点击上方按钮创建</p>
      </div>
      <div class="card agent-card" v-for="agent in agents" :key="agent.id">
        <div class="agent-header">
          <h3>{{ agent.name }}</h3>
          <span :class="['status-badge', agent.is_active ? 'active' : 'inactive']">
            {{ agent.is_active ? '活跃' : '停用' }}
          </span>
        </div>
        <p class="agent-desc">{{ agent.description || '无描述' }}</p>
        <div class="agent-scopes" v-if="agent.health_data_scope?.length">
          <span class="scope-tag" v-for="s in agent.health_data_scope" :key="s">{{ scopeLabels[s] || s }}</span>
        </div>
        <div class="agent-actions">
          <button class="btn btn-outline" @click="openEdit(agent)">编辑</button>
          <button class="btn btn-danger" @click="deleteAgent(agent.id)">删除</button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Form -->
    <div class="card form-card" v-if="showForm">
      <h2>{{ editingId ? '编辑智能体' : '创建智能体' }}</h2>
      <form @submit.prevent="saveAgent">
        <div class="form-group">
          <label>名称</label>
          <input v-model="form.name" class="input" placeholder="例如：睡眠教练" required />
        </div>
        <div class="form-group">
          <label>描述</label>
          <input v-model="form.description" class="input" placeholder="简要描述智能体的功能" />
        </div>
        <div class="form-group">
          <label>系统提示词</label>
          <textarea v-model="form.system_prompt" class="textarea" rows="5"
            placeholder="定义智能体的角色和行为，例如：你是一个专业的睡眠优化教练..." required></textarea>
        </div>
        <div class="form-group">
          <label>数据访问范围</label>
          <div class="scope-select">
            <button type="button" v-for="s in dataScopes" :key="s"
              :class="['scope-btn', { selected: form.health_data_scope?.includes(s) }]"
              @click="toggleScope(s)">
              {{ scopeLabels[s] }}
            </button>
          </div>
        </div>
        <div class="form-actions">
          <button type="button" class="btn btn-outline" @click="showForm = false">取消</button>
          <button type="submit" class="btn btn-primary">保存</button>
        </div>
      </form>
    </div>
  </div>
</template>

<style scoped>
.loading, .empty { text-align: center; padding: 40px; color: var(--color-text-secondary); }
.agents-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(340px, 1fr)); gap: 16px; }
.agent-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.agent-header h3 { font-size: 16px; }
.status-badge { font-size: 12px; padding: 2px 8px; border-radius: 10px; }
.status-badge.active { background: #ECFDF5; color: #10B981; }
.status-badge.inactive { background: #FEF2F2; color: #EF4444; }
.agent-desc { font-size: 13px; color: var(--color-text-secondary); margin-bottom: 12px; }
.agent-scopes { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 16px; }
.scope-tag { font-size: 11px; padding: 2px 8px; background: #EEF2FF; color: var(--color-primary); border-radius: 4px; }
.agent-actions { display: flex; gap: 8px; }
.agent-actions .btn { padding: 6px 14px; font-size: 13px; }
.form-card { max-width: 640px; }
.form-card h2 { margin-bottom: 24px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; font-size: 13px; font-weight: 600; margin-bottom: 6px; color: var(--color-text-secondary); }
.scope-select { display: flex; flex-wrap: wrap; gap: 8px; }
.scope-btn { padding: 6px 14px; border: 1px solid var(--color-border); border-radius: 6px; font-size: 13px; background: white; }
.scope-btn.selected { background: var(--color-primary); color: white; border-color: var(--color-primary); }
.form-actions { display: flex; gap: 12px; justify-content: flex-end; margin-top: 24px; }
</style>
