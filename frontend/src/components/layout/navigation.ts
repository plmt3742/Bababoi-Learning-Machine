import {
  IconBarChart,
  IconBook,
  IconHome,
  IconList,
  IconPen,
  IconSettings,
} from '@arco-design/web-vue/es/icon'
import type { Component } from 'vue'

export interface NavigationItem {
  key: string
  label: string
  icon: Component
  to?: string
  badge?: string
  disabled?: boolean
  mobile?: boolean
}

/**
 * Sidebar order mirrors docs/product/04-design-system.md: primary flow first,
 * P1 destinations marked, settings reserved until its page exists.
 */
export const navigationItems: NavigationItem[] = [
  { key: 'home', label: '首页', icon: IconHome, to: '/', mobile: true },
  { key: 'questions', label: '错题本', icon: IconBook, to: '/questions', mobile: true },
  { key: 'tasks', label: '任务中心', icon: IconList, to: '/tasks', mobile: true },
  { key: 'practice', label: '练习', icon: IconPen, to: '/practice', mobile: true },
  { key: 'stats', label: '统计', icon: IconBarChart, to: '/stats', badge: 'P1' },
  { key: 'settings', label: '设置', icon: IconSettings, badge: 'P1', disabled: true },
]

/** Thumb-reachable destinations for the 375px bottom bar. */
export const primaryNavigation = navigationItems.filter(
  (item): item is NavigationItem & { to: string } => item.mobile === true && item.to !== undefined,
)
