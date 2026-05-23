import { createApp } from 'vue'
import App from './App.vue'
import { createPinia } from 'pinia'
import router from './router'

const app = createApp(App)
app.use(createPinia())  //  状态管理
app.use(router)  //  路由
app.mount('#app')
