import { createApp } from 'vue'
import './styles/tokens.css'
import './styles/arco-theme.css'
import './styles/global.css'
import App from './App.vue'
import router from './router'
import { setUnauthorizedHandler } from './api/client'
import { useAuthStore } from './stores/auth'
import { pinia } from './stores'

async function bootstrap(): Promise<void> {
  const app = createApp(App)
  app.use(pinia)

  // Dev-only in-memory backend. Dynamic import keeps mock data out of production.
  if (import.meta.env.DEV && import.meta.env.VITE_USE_MOCK !== 'false') {
    const { setupMocks } = await import('./api/mocks')
    setupMocks()
  }

  const auth = useAuthStore(pinia)

  setUnauthorizedHandler(() => {
    auth.logout()
    void router
      .isReady()
      .then(() => {
        const current = router.currentRoute.value
        if (current.name === 'login') return

        void router.replace({
          name: 'login',
          query: { redirect: current.fullPath },
        })
      })
      .catch(() => {
        // The client's full-page fallback handles a router that never started.
      })
  })

  await auth.restore()

  app.use(router)
  app.mount('#app')
}

void bootstrap()
