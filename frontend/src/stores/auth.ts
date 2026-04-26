import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export const useAuthStore = defineStore('auth', () => {
    const accessToken = ref('')
    const expiresAt = ref(0)
    let expiresTimer: ReturnType<typeof window.setTimeout> | undefined

    // 计算accessToken是否过期
    const isAccessTokenExpired = computed(() => {
        return expiresAt.value > 0 && expiresAt.value <= Date.now()
    })

    const isAuthenticated = computed(() => {
        return accessToken.value.length > 0 && !isAccessTokenExpired.value
    })

    const clearExpiresTimer = () => {
        if (expiresTimer !== undefined) {
            window.clearTimeout(expiresTimer)
            expiresTimer = undefined
        }
    }

    const scheduleTokenCleanup = () => {
        clearExpiresTimer()

        if (!accessToken.value || expiresAt.value <= 0) {
            return
        }

        const delay = expiresAt.value - Date.now()

        if (delay <= 0) {
            clearAccessToken()
            return
        }

        expiresTimer = window.setTimeout(() => {
            clearAccessToken()
        }, delay)
    }

    // 设置accessToken
    const setAccessToken = (token: string, tokenExpiresAt: number) => {
        accessToken.value = token
        expiresAt.value = tokenExpiresAt
    }

    // 清除accessToken
    const clearAccessToken = () => {
        clearExpiresTimer()
        accessToken.value = ''
        expiresAt.value = 0
    }

    // 获取accessToken
    const getAccessToken = () => {
        if (isAccessTokenExpired.value) {
            clearAccessToken()
            return ''
        }

        return accessToken.value
    }

    watch(expiresAt, scheduleTokenCleanup)

    return {
        isAccessTokenExpired,
        isAuthenticated,
        setAccessToken,
        clearAccessToken,
        getAccessToken,
    }
})
