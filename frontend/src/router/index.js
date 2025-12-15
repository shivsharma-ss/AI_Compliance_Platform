import { createRouter, createWebHistory } from 'vue-router'
import LoginView from '../views/Login.vue'

const router = createRouter({
    history: createWebHistory(import.meta.env.BASE_URL),
    routes: [
        {
            path: '/login',
            name: 'login',
            component: LoginView
        },
        {
            path: '/',
            name: 'home',
            component: () => import('../views/UserDashboard.vue'),
            meta: { requiresAuth: true }
        },
        {
            path: '/admin',
            name: 'admin',
            component: () => import('../views/AdminDashboard.vue'),
            meta: { requiresAuth: true, requiresAdmin: true }
        }
    ]
})

import { jwtDecode } from "jwt-decode";

// Navigation Guard
router.beforeEach((to, from, next) => {
    const token = localStorage.getItem('token')

    if (to.meta.requiresAuth && !token) {
        next('/login')
        return
    }

    if (token) {
        try {
            const decoded = jwtDecode(token)
            const isTokenExpired = decoded.exp < Date.now() / 1000

            if (isTokenExpired) {
                localStorage.removeItem('token')
                next('/login')
                return
            }

            if (to.meta.requiresAdmin && decoded.role !== 'admin') {
                next('/') // Redirect unauthorized users to home
                return
            }
        } catch (e) {
            localStorage.removeItem('token')
            next('/login')
            return
        }
    }

    next()
})

export default router
