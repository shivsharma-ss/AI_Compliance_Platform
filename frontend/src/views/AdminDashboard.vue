<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const rules = ref([])
const stats = ref([])
const selectedUserHistory = ref([])
const selectedUserEmail = ref('')
const showHistoryModal = ref(false)

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

const fetchStats = async () => {
  try {
    const response = await axios.get('http://localhost:8000/api/v1/admin/users/stats', {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    stats.value = response.data
  } catch (error) {
    console.error('Failed to fetch stats', error)
  }
}

const viewUserHistory = async (user) => {
  selectedUserEmail.value = user.email
  try {
    const response = await axios.get(`http://localhost:8000/api/v1/admin/users/${user.id}/history`, {
      headers: { Authorization: `Bearer ${authStore.token}` }
    })
    selectedUserHistory.value = response.data
    showHistoryModal.value = true
  } catch (error) {
    console.error('Failed to fetch user history', error)
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
  fetchStats()
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
        <!-- Rule Management Section -->
        <div class="section-left">
          <div class="card mb-2">
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
                <div class="rule-info">
                  <strong>{{ rule.name }}</strong>
                  <code class="pattern">{{ rule.payload_json?.pattern }}</code>
                </div>
                <span class="badge" :class="rule.severity.toLowerCase()">{{ rule.severity }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- User Analytics Section -->
        <div class="section-right">
          <div class="card">
            <h2>User Analytics</h2>
            <table class="stats-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Total</th>
                  <th>Accepted</th>
                  <th>Declined</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="user in stats" :key="user.id">
                  <td>{{ user.email }}</td>
                  <td>{{ user.total_prompts }}</td>
                  <td class="text-success">{{ user.accepted_count }}</td>
                  <td class="text-danger">{{ user.declined_count }}</td>
                  <td>
                    <button @click="viewUserHistory(user)" class="btn-sm btn-outline-primary">View History</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </main>

    <!-- History Modal -->
    <div v-if="showHistoryModal" class="modal-overlay" @click.self="showHistoryModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h3>History for: {{ selectedUserEmail }}</h3>
          <button @click="showHistoryModal = false" class="close-btn">&times;</button>
        </div>
        <div class="modal-body">
          <div v-if="selectedUserHistory.length === 0">No history found.</div>
          <div v-else class="history-list">
             <div v-for="item in selectedUserHistory" :key="item.id" class="history-item">
              <div class="history-header">
                <span class="badge" :class="item.decision?.toLowerCase()">{{ item.decision }}</span>
                <span class="date">{{ new Date(item.created_at).toLocaleString() }}</span>
              </div>
              <p class="history-prompt">{{ item.prompt_text }}</p>
              <small class="reason">{{ item.reason_summary }}</small>
            </div>
          </div>
        </div>
      </div>
    </div>
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
  grid-template-columns: 1fr 1.5fr; /* 1 column for rules, 1.5 for stats */
  gap: 2rem;
}
.mb-2 { margin-bottom: 2rem; }
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
  display: block;
  background: #f8f9fa;
  padding: 0.2rem 0.4rem;
  border-radius: 4px;
  font-family: monospace;
  font-size: 0.85em;
  margin-top: 0.2rem;
  color: #666;
}
.badge {
  padding: 0.2rem 0.5rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: bold;
}
.badge.block, .badge.decline { background: #f8d7da; color: #721c24; }
.badge.warn { background: #ffc107; color: black; }
.badge.accept { background: #d4edda; color: #155724; }

/* Table Styles */
.stats-table {
  width: 100%;
  border-collapse: collapse;
  margin-top: 1rem;
}
.stats-table th, .stats-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #dee2e6;
  text-align: left;
}
.stats-table th { background: #f8f9fa; }
.text-success { color: #28a745; font-weight: bold; }
.text-danger { color: #dc3545; font-weight: bold; }
.btn-sm {
  padding: 0.25rem 0.5rem;
  font-size: 0.85rem;
}
.btn-outline-primary {
  border: 1px solid var(--color-primary);
  color: var(--color-primary);
  background: transparent;
  border-radius: 4px;
}
.btn-outline-primary:hover {
  background: var(--color-primary);
  color: white;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}
.modal-content {
  background: white;
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
}
.modal-header {
  padding: 1rem;
  border-bottom: 1px solid #dee2e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.modal-body {
  padding: 1rem;
  overflow-y: auto;
}
.close-btn {
  background: none;
  font-size: 1.5rem;
  cursor: pointer;
}
.history-item {
  border-bottom: 1px solid #eee;
  padding: 1rem 0;
}
.reason {
  color: #666;
  font-style: italic;
}
@media (max-width: 900px) {
  .grid { grid-template-columns: 1fr; }
}
</style>
