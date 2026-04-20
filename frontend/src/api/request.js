import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api', // Vite 代理或 Nginx 会自动转发
  timeout: 10000
})

// 请求拦截器：自动注入 JWT Token
service.interceptors.request.use(
  config => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  error => Promise.reject(error)
)

// 响应拦截器：统一处理报错
service.interceptors.response.use(
  response => response.data,
  error => {
    const msg = error.response?.data?.detail || '网络请求异常'
    ElMessage.error(msg)
    if (error.response?.status === 401) {
      // Token 过期，清除并跳回登录页
      localStorage.clear()
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default service
