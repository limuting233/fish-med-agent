import { createRouter, createWebHistory } from 'vue-router'

import LoginView from '../views/LoginView.vue'
import HomeView from '../views/HomeView.vue'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
    history: createWebHistory(),
    routes: [
        {
            path: '/',
            redirect: '/home',
        },
        {
            path: '/login',
            name: 'login',
            component: LoginView,
        },
        {
            path: '/home',
            name: 'home',
            component: HomeView,
        },
    ],
})

router.beforeEach((to) => {
    const authStore = useAuthStore()
    const isLoginPage = to.name === 'login'
    if (!authStore.isAuthenticated && !isLoginPage) {
        return {
            name: 'login',
            query: {
                redirect: to.fullPath,
            },
        }
    }

    if (authStore.isAuthenticated && isLoginPage) {
        return {
            name: 'home',
        }
    }
})

export default router
