/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_ADMIN_DEMO?: string
  readonly VITE_ADMIN_DEMO_USERNAME?: string
  readonly VITE_ADMIN_DEMO_PASSWORD?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
