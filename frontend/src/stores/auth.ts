import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'

export const useAuthStore = defineStore('auth', () => {
    const accessToken = ref('')
    const expiresAt = ref(0)
    const username = ref('')
    const nickname = ref('')
    const avatarUrl = ref('')
    const isActive = ref(true)
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
    const setAccessToken = (token: string, tokenExpiresAt: number, accountUsername = '', accountNickname = '', accountAvatarUrl = '', accountIsActive = true) => {
        accessToken.value = token
        expiresAt.value = tokenExpiresAt
        username.value = accountUsername
        nickname.value = accountNickname
        avatarUrl.value = accountAvatarUrl
        isActive.value = accountIsActive
    }

    const setToken = (token: string, tokenExpiresAt: number) => {
        accessToken.value = token
        expiresAt.value = tokenExpiresAt
    }

    const setUserProfile = (profile: { username?: string | null; nickname?: string | null; avatarUrl?: string | null; isActive?: boolean | null }) => {
        username.value = profile.username ?? username.value
        nickname.value = profile.nickname ?? nickname.value
        avatarUrl.value = profile.avatarUrl ?? avatarUrl.value
        isActive.value = profile.isActive ?? isActive.value
    }

    // 清除accessToken
    const clearAccessToken = () => {
        clearExpiresTimer()
        accessToken.value = ''
        expiresAt.value = 0
        username.value = ''
        nickname.value = ''
        avatarUrl.value = ''
        isActive.value = true
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
        username,
        nickname,
        avatarUrl,
        isActive,
        setAccessToken,
        setToken,
        setUserProfile,
        clearAccessToken,
        getAccessToken,
    }
})
