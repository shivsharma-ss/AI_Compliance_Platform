<script setup>
import { ref } from 'vue'
import { useAuthStore } from '../stores/auth'

const email = ref('')
const password = ref('')
const authStore = useAuthStore()

const handleLogin = async () => {
  await authStore.login(email.value, password.value)
}
</script>

<template>
  <div class="login-container">
    <div class="card">
      <h1>Sentinel Gateway</h1>
      <p class="subtitle">AI Governance & Compliance</p>
      
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>Email</label>
          <input type="email" v-model="email" required class="input" placeholder="analyst@sentinel.ai" />
        </div>
        
        <div class="form-group">
          <label>Password</label>
          <input type="password" v-model="password" required class="input" placeholder="******" />
        </div>
        
        <div v-if="authStore.error" class="error">
          {{ authStore.error }}
        </div>
        
        <button type="submit" class="btn btn-primary full-width">Sign In</button>
      </form>
    </div>
  </div>
</template>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: var(--color-bg-soft);
}

.card {
  background: white;
  padding: 2rem;
  border-radius: 12px;
  box-shadow: var(--shadow-md);
  width: 100%;
  max-width: 400px;
}

h1 {
  text-align: center;
  margin-bottom: 0.5rem;
  color: var(--color-primary);
}

.subtitle {
  text-align: center;
  color: var(--color-text-light);
  margin-bottom: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.full-width {
  width: 100%;
  margin-top: 1rem;
}

.error {
  color: var(--color-danger);
  font-size: 0.9rem;
  margin-top: 0.5rem;
  text-align: center;
}
</style>
