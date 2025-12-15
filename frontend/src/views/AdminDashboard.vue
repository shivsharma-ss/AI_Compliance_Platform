<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const rules = ref([])
const newRuleName = ref('')
const newRulePattern = ref('')
const loading = ref(false)

const fetchRules = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/v1/rules/', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    rules.value = response.data
  } catch (error) {
    console.error('Failed to fetch rules', error)
  }
}

const addRule = async () => {
  if (!newRuleName.value || !newRulePattern.value) return
  loading.value = true
  try {
    await axios.post('http://localhost:8000/api/v1/rules/', {
      name: newRuleName.value,
      description: 'Added via Admin Dashboard',
      type: 'REGEX',
      payload_json: { pattern: newRulePattern.value },
      severity: 'BLOCK',
      is_active: true
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    newRuleName.value = ''
    newRulePattern.value = ''
    await fetchRules()
    alert('Rule added successfully')
  } catch (error) {
    console.error(error)
    alert('Failed to add rule')
  } finally {
    loading.value = false
  }
}

const logout = () => {
  authStore.logout()
}

onMounted(() => {
  fetchRules()
})
</script>

<template>
  <div class="dashboard">
    <header class="header">
      <div class="container header-content">
        <div class="logo">Spotixx Admin</div>
        <div class="user-info">
          <span>{{ authStore.user?.email }}</span>
          <button @click="logout" class="btn btn-outline">Logout</button>
        </div>
      </div>
    </header>

    <main class="container">
      <div class="grid">
        <div class="card">
          <h2>Add New Rule</h2>
          <form @submit.prevent="addRule">
            <div class="form-group">
              <label>Rule Name</label>
              <input v-model="newRuleName" class="input" placeholder="e.g. Block LSD" required />
            </div>
            <div class="form-group">
              <label>Regex Pattern</label>
              <input v-model="newRulePattern" class="input" placeholder="e.g. (?i)lsd|acid" required />
            </div>
            <button type="submit" class="btn btn-primary full-width" :disabled="loading">
              {{ loading ? 'Saving...' : 'Add Block Rule' }}
            </button>
          </form>
        </div>

        <div class="card">
          <h2>Active Rules</h2>
          <div class="rules-list">
            <div v-for="rule in rules" :key="rule.id" class="rule-item">
              <strong>{{ rule.name }}</strong>
              <code class="pattern">{{ rule.payload_json?.pattern }}</code>
              <span class="badge" :class="rule.severity.toLowerCase()">{{ rule.severity }}</span>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.header {
  background: #343a40;
  color: white;
  padding: 1rem 0;
  margin-bottom: 2rem;
}
.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.logo { font-weight: bold; font-size: 1.2rem; }
.btn-outline {
  border: 1px solid white;
  color: white;
  background: transparent;
  margin-left: 1rem;
}
.grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}
.card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0,0,0,0.1);
}
.form-group { margin-bottom: 1rem; }
.rules-list { margin-top: 1rem; }
.rule-item {
  border-bottom: 1px solid #eee;
  padding: 0.5rem 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.pattern {
  background: #f8f9fa;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.9em;
}
.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
}
.badge.block { background: #dc3545; color: white; }
.badge.warn { background: #ffc107; color: black; }
</style>
