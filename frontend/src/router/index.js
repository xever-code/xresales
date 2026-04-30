import { createRouter, createWebHistory } from 'vue-router'
import { ElMessage } from 'element-plus'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue')
  },
  {
    path: '/',
    name: 'Layout',
    component: () => import('../views/Layout.vue'),
    redirect: '/input',
    children: [
      {
        path: 'input',
        name: 'Input',
        component: () => import('../views/Input.vue'),
        meta: { title: '工时录入' }
      },
      {
        path: 'report',
        name: 'Report',
        component: () => import('../views/Report.vue'),
        meta: { title: '统计分析' }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('../views/Logs.vue'),
        meta: { title: '查看记录' }
      },
      {
        path: 'changelog',
        name: 'Changelog',
        component: () => import('../views/Changelog.vue'),
        meta: { title: '更新日志' }
      },
      {
        path: 'hospitals',
        name: 'Hospitals',
        component: () => import('../views/Hospitals.vue'),
        meta: { title: '客户管理', requiresAdmin: true }
      },
      {
        path: '/users',
        name: 'UserManage',
        component: () => import('../views/UserManage.vue'),
        meta: { requiresAuth: true, role: 'admin' } // 确保只有管理员可进入
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 路由守卫：未登录跳登录页，越权访问跳首页
router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('access_token')
  const role = localStorage.getItem('role')

  if (to.path !== '/login' && !token) {
    next('/login')
  } else if (to.meta.requiresAdmin && role !== 'admin') {
    ElMessage.error('权限不足，仅管理员可访问此页面')
    next('/')
  } else {
    next()
  }
})

export default router
