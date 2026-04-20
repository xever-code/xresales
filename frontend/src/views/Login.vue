<template>
  <div class="login-container">
    <el-card class="login-card" shadow="always">
      <div class="logo-title">
        <h2>🔐 Digital Consulting</h2>
        <p class="subtitle">售前工作管理系统</p>
      </div>
      
      <el-form :model="form" @keyup.enter="handleLogin">
        <el-form-item>
          <el-input 
            v-model="form.username" 
            placeholder="请输入账号 (开机用户名)" 
            size="large" 
            :prefix-icon="User" />
        </el-form-item>
        <el-form-item>
          <el-input 
            v-model="form.password" 
            type="password" 
            placeholder="请输入密码 (默认: 123456)" 
            size="large" 
            :prefix-icon="Lock" 
            show-password />
        </el-form-item>
        <el-button 
          type="primary" 
          size="large" 
          class="login-btn" 
          :loading="loading" 
          @click="handleLogin">
          登 录 系 统
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../api/request' // 引入之前配置的 axios 实例

const router = useRouter()
const form = ref({ username: '', password: '' })
const loading = ref(false)

const handleLogin = async () => {
  if (!form.value.username || !form.value.password) {
    ElMessage.warning('请输入完整的账号和密码')
    return
  }
  
  loading.value = true
  try {
    // FastAPI OAuth2 规范要求使用 FormData (x-www-form-urlencoded)
    const formData = new FormData()
    formData.append('username', form.value.username)
    formData.append('password', form.value.password)

    const res = await request.post('/auth/login', formData)
    
    // 缓存用户信息
    localStorage.setItem('access_token', res.access_token)
    localStorage.setItem('role', res.role)
    localStorage.setItem('real_name', res.real_name)
    localStorage.setItem('username', res.username)
    
    ElMessage.success(`欢迎回来，${res.real_name}`)
    // 跳转到后台首页
    router.push('/')
  } catch (error) {
    // 错误已经在 request.js 中通过拦截器处理过了，这里无需再写 ElMessage
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  /* 现代风格的渐变背景 */
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  box-sizing: border-box;
}

.login-card {
  width: 100%;
  max-width: 400px; /* PC 端最大宽度限制 */
  border-radius: 16px;
  box-shadow: 0 10px 25px rgba(0,0,0,0.2) !important;
  border: none;
}

.logo-title {
  text-align: center;
  margin-bottom: 30px;
}

.logo-title h2 {
  color: #409EFF;
  margin: 0 0 10px 0;
  font-size: 24px;
}

.subtitle {
  color: #909399;
  font-size: 14px;
  margin: 0;
}

.login-btn {
  width: 100%;
  font-weight: bold;
  border-radius: 8px;
  margin-top: 10px;
}
</style>
