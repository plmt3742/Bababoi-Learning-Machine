import { IconBook, IconEdit, IconList, IconPen } from '@arco-design/web-vue/es/icon'
import type { Component } from 'vue'

export interface NavigationItem {
  key: string
  label: string
  to: string
  icon?: Component
}

/** Calm appbar: the three destinations in the approved prototype. */
export const topNavigation: NavigationItem[] = [
  { key: 'questions', label: '错题本', to: '/questions' },
  { key: 'create', label: '录入错题', to: '/questions/new' },
  { key: 'tasks', label: '任务中心', to: '/tasks' },
]

/** Mobile thumb bar: keep the same flow, plus practice. */
export const mobileNavigation: NavigationItem[] = [
  { key: 'questions', label: '错题', to: '/questions', icon: IconBook },
  { key: 'create', label: '录入', to: '/questions/new', icon: IconEdit },
  { key: 'tasks', label: '任务', to: '/tasks', icon: IconList },
  { key: 'practice', label: '练习', to: '/practice', icon: IconPen },
]
