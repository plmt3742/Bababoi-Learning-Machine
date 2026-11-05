import 'vue-router'

declare module 'vue-router' {
  interface RouteMeta {
    /** Document title and top-bar label. */
    title: string
    /** Sidebar item to highlight; absent for standalone pages such as 404. */
    navKey?: string
    /** Redirect to /login when there is no token. */
    requiresAuth?: boolean
  }
}
