import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

export const useAuthStore = defineStore('auth', () => {
    const accessToken = ref('')

    const isAuthenticated = computed(() => {
        return accessToken.value.length > 0
    })

    // 设置accessToken
    const setAccessToken = (token: string) => {
        accessToken.value = token
    }

    // 清除accessToken
    const clearAccessToken = () => {
        accessToken.value = ''
    }

    // 获取accessToken
    const getAccessToken = () => {
        return accessToken.value
    }

    return {
       
        isAuthenticated,
        setAccessToken,
        clearAccessToken,
        getAccessToken,
    }
})
