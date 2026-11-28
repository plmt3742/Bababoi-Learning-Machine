import { createApp } from 'vue'
import ArcoVue from '@arco-design/web-vue'
import '@arco-design/web-vue/dist/arco.css'

import App from './App.vue'
import router from './router'
import { pinia } from './stores'
import './styles/admin.css'
import './styles/calm-alignment.css'

const app = createApp(App)

app.use(pinia)
app.use(ArcoVue)
app.use(router)
app.mount('#app')
