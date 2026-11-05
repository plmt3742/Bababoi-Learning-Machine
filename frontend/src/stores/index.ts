import { createPinia } from 'pinia'

/** Single Pinia instance shared by the app, router guards and the 401 handler. */
export const pinia = createPinia()
