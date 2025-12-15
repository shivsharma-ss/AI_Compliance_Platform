import { defineStore } from 'pinia'
import axios from 'axios'
import { jwtDecode } from "jwt-decode";
import router from '../router'

export const useAuthStore = defineStore('auth', {
    state: () => ({
        token: localStorage.getItem('token') || null,
        user: null,
        error: null
    }),
    getters: {
        isAuthenticated: (state) => !!state.token,
        isAdmin: (state) => state.user?.role === 'admin'
    },
    actions: {
        async login(email, password) {
            try {
                // Use relative URL assuming proxy or localhost direct access
                // Ideally from env var
                const response = await axios.post('http://localhost:8000/api/v1/auth/login',
                    new URLSearchParams({
                        'username': email,
                        'password': password
                    })
                )
                const token = response.data.access_token
                this.token = token
                localStorage.setItem('token', token)

                // Decode user info
                const decoded = jwtDecode(token)
                this.user = {
                    id: decoded.sub,
                    role: decoded.role
                }

                if (this.user.role === 'admin') {
                    router.push('/admin')
                } else {
                    router.push('/')
                }
            } catch (err) {
                console.error(err)
                this.error = err.response?.data?.detail || 'Login failed'
            }
        },
        logout() {
            this.token = null
            this.user = null
            localStorage.removeItem('token')
            router.push('/login')
        }
    }
})
