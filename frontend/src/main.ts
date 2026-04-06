import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './assets/styles/main.css'

const app = createApp(App)//这个地方App参数指的是App作为整个应用的最顶层根组件，是页面渲染的起点
app.use(createPinia())
app.use(router)
app.mount('#app')
