<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'
const promptText = ref('')
const intendedUse = ref('Fraud investigation')
const context = ref('')
const history = ref([])
const loading = ref(false)
const currentResult = ref(null)

const submitPrompt = async () => {
  loading.value = true
  currentResult.value = null
  try {
    const response = await axios.post(`${API_BASE}/api/v1/prompts/evaluate`, {
      prompt_text: promptText.value,
      intended_use: intendedUse.value,
      context: context.value
    }, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    currentResult.value = response.data
    await fetchHistory() // Refresh history
  } catch (error) {
    console.error(error)
    alert('Failed to submit prompt')
  } finally {
    loading.value = false
  }
}

const fetchHistory = async () => {
  try {
    const response = await axios.get(`${API_BASE}/api/v1/prompts/history`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    history.value = response.data
  } catch (error) {
    console.error(error)
  }
}

const logout = () => {
  authStore.logout()
}

onMounted(() => {
  fetchHistory()
})
</script>

<template>
  <div class="dashboard">
    <header class="header">
      <div class="container header-content">
        <div class="logo">Sentinel Gateway</div>
        <div class="user-info">
          <span>{{ authStore.user?.role }}</span>
          <button @click="logout" class="btn btn-outline">Logout</button>
        </div>
      </div>
    </header>

    <main class="container main-content">
      <div class="grid">
        <!-- Submission Form -->
        <div class="card form-card">
          <h2>Submit Prompt</h2>
          <form @submit.prevent="submitPrompt">
            <div class="form-group">
              <label>Intended Use</label>
              <select v-model="intendedUse" class="input">
                <option>Fraud investigation</option>
                <option>AML narrative drafting</option>
                <option>Customer comms</option>
                <option>Other</option>
              </select>
            </div>
            
            <div class="form-group">
              <label>Prompt Text</label>
              <textarea v-model="promptText" rows="6" required class="input" placeholder="Enter your prompt here..."></textarea>
            </div>

            <div class="form-group">
              <label>Context (Optional)</label>
              <input v-model="context" class="input" placeholder="Additional context..." />
            </div>

            <button type="submit" class="btn btn-primary full-width" :disabled="loading">
              {{ loading ? 'Evaluating...' : 'Check Compliance' }}
            </button>
          </form>

          <!-- Result Display -->
          <div v-if="currentResult" class="result" :class="currentResult.decision.toLowerCase()">
            <h3>Decision: {{ currentResult.decision }}</h3>
            <p>{{ currentResult.reason_summary }}</p>
          </div>
        </div>

        <!-- History -->
        <div class="card history-card">
          <h2>Recent Requests</h2>
          <div class="history-list">
            <div v-for="item in history" :key="item.id" class="history-item">
              <div class="history-header">
                <span class="badge" :class="item.decision?.toLowerCase()">{{ item.decision || 'PENDING' }}</span>
                <span class="date">{{ new Date(item.created_at).toLocaleDateString() }}</span>
              </div>
              <p class="history-prompt">{{ item.prompt_text }}</p>
              <small>{{ item.intended_use }}</small>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.header {
  background: white;
  box-shadow: var(--shadow-sm);
  padding: 1rem 0;
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  font-weight: bold;
  font-size: 1.2rem;
  color: var(--color-primary);
}

.grid {
  display: grid;
  grid-template-columns: 1fr;
  gap: 2rem;
}

@media (min-width: 768px) {
  .grid {
    grid-template-columns: 1.2fr 0.8fr;
  }
}

.card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: var(--shadow-sm);
}

.form-group {
  margin-bottom: 1rem;
}

.result {
  margin-top: 1.5rem;
  padding: 1rem;
  border-radius: 6px;
  background: #f8f9fa;
  border-left: 4px solid #ccc;
}

.result.accept {
  border-left-color: var(--color-success);
  background: #d4edda;
  color: #155724;
}

.result.decline {
  border-left-color: var(--color-danger);
  background: #f8d7da;
  color: #721c24;
}

.history-list {
  max-height: 500px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.history-item {
  border-bottom: 1px solid var(--color-border);
  padding-bottom: 1rem;
}

.history-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 0.5rem;
}

.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
}

.badge.accept { background: #d4edda; color: #155724; }
.badge.decline { background: #f8d7da; color: #721c24; }

.history-prompt {
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: var(--color-text);
  margin-bottom: 0.2rem;
}
</style>
