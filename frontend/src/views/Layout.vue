<template>
  <el-container class="layout-container">
    
    <el-aside width="220px" class="pc-aside">
      <div class="logo">IT售前工时管理系统</div>
      <el-menu :default-active="route.path" router class="aside-menu" background-color="#001529" text-color="#a6adb4" active-text-color="#ffffff">
        <el-menu-item index="/input">
          <el-icon><Edit /></el-icon><span>工时录入</span>
        </el-menu-item>
        <el-menu-item index="/report">
          <el-icon><TrendCharts /></el-icon><span>统计分析</span>
        </el-menu-item>
        <el-menu-item index="/logs">
          <el-icon><List /></el-icon><span>查看记录</span>
        </el-menu-item>
        
        <el-menu-item index="/changelog">
          <el-icon><Document /></el-icon><span>更新日志</span>
        </el-menu-item>

        <template v-if="userRole === 'admin'">
          <div class="menu-divider">管理员功能</div>
          <el-menu-item index="/hospitals">
            <el-icon><OfficeBuilding /></el-icon><span>客户管理</span>
          </el-menu-item>
          <el-menu-item index="/users">
            <el-icon><User /></el-icon><span>用户管理</span>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-drawer v-model="drawerVisible" direction="ltr" size="240px" :with-header="false">
      <div class="logo mobile-logo">DC 管理系统</div>
      <el-menu :default-active="route.path" router @select="drawerVisible = false" background-color="#001529" text-color="#a6adb4" active-text-color="#ffffff" style="height: calc(100vh - 60px);">
        <el-menu-item index="/input"><el-icon><Edit /></el-icon><span>工时录入</span></el-menu-item>
        <el-menu-item index="/report"><el-icon><TrendCharts /></el-icon><span>统计分析</span></el-menu-item>
        
        <el-menu-item index="/changelog"><el-icon><Document /></el-icon><span>更新日志</span></el-menu-item>

        <template v-if="userRole === 'admin'">
          <div class="menu-divider">管理员功能</div>
          <el-menu-item index="/hospitals"><el-icon><OfficeBuilding /></el-icon><span>客户管理</span></el-menu-item>
          <el-menu-item index="/users"><el-icon><User /></el-icon><span>用户管理</span></el-menu-item>
        </template>
      </el-menu>
    </el-drawer>

    <el-container>
      <el-header class="main-header">
        <div class="header-left">
          <el-icon class="hamburger" @click="drawerVisible = true"><Expand /></el-icon>
          <span class="page-title">{{ route.meta.title || '售前管理' }}</span>
        </div>
        
        <div class="header-right">
          <el-dropdown @command="handleCommand" trigger="click">
            <span class="user-dropdown">
              <el-avatar :size="32" style="background: #409EFF;">{{ realName?.charAt(0) }}</el-avatar>
              <span class="username">{{ realName }}</span>
              <el-icon><ArrowDown /></el-icon>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="password">修改密码</el-dropdown-item>
                <el-dropdown-item command="logout" divided style="color: #F56C6C;">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main-content">
        <router-view v-slot="{ Component }">
          <transition name="fade-transform" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>

    <el-dialog v-model="pwdDialogVisible" title="修改密码" width="400px" destroy-on-close>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="100px">
        <el-form-item label="原密码" prop="old_password">
          <el-input v-model="pwdForm.old_password" type="password" show-password placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="new_password">
          <el-input v-model="pwdForm.new_password" type="password" show-password placeholder="请输入新密码(至少6位)" />
        </el-form-item>
        <el-form-item label="确认新密码" prop="confirm_password">
          <el-input v-model="pwdForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="pwdDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="pwdSubmitting" @click="submitPasswordChange">确认修改</el-button>
        </span>
      </template>
    </el-dialog>

  </el-container>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
// 👇 导入 Document 图标
import { Expand, Edit, TrendCharts, OfficeBuilding, User, ArrowDown, Document } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

const router = useRouter()
const route = useRoute()

const drawerVisible = ref(false)
const userRole = ref(localStorage.getItem('role') || 'user')
const realName = ref(localStorage.getItem('real_name') || '用户')

const pwdDialogVisible = ref(false)
const pwdFormRef = ref(null)
const pwdSubmitting = ref(false)
const pwdForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: ''
})

const validateConfirmPwd = (rule, value, callback) => {
  if (value !== pwdForm.new_password) {
    callback(new Error('两次输入的新密码不一致!'))
  } else {
    callback()
  }
}

const pwdRules = {
  old_password: [{ required: true, message: '请输入原密码', trigger: 'blur' }],
  new_password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  confirm_password: [
    { required: true, message: '请再次输入新密码', trigger: 'blur' },
    { validator: validateConfirmPwd, trigger: 'blur' }
  ]
}

const handleCommand = (command) => {
  if (command === 'logout') {
    localStorage.clear()
    router.push('/login')
  } else if (command === 'password') {
    pwdForm.old_password = ''
    pwdForm.new_password = ''
    pwdForm.confirm_password = ''
    pwdDialogVisible.value = true
  }
}

const submitPasswordChange = async () => {
  if (!pwdFormRef.value) return
  await pwdFormRef.value.validate(async (valid) => {
    if (valid) {
      pwdSubmitting.value = true
      try {
        await request.post('/auth/password', {
          old_password: pwdForm.old_password,
          new_password: pwdForm.new_password
        })
        ElMessage.success('密码修改成功，请重新登录！')
        pwdDialogVisible.value = false
        localStorage.clear()
        router.push('/login')
      } catch (error) {
        // 错误已经在 request.js 统一处理
      } finally {
        pwdSubmitting.value = false
      }
    }
  })
}
</script>

<style scoped>
/* 保持原有样式不变 */
.layout-container {
  height: 100vh;
  width: 100vw;
  overflow: hidden;
}
.pc-aside {
  background-color: #001529;
  transition: width 0.3s;
  display: flex;
  flex-direction: column;
}
.logo {
  height: 60px;
  line-height: 60px;
  text-align: center;
  color: white;
  font-size: 18px;
  font-weight: bold;
  background-color: #002140;
}
.aside-menu {
  border-right: none;
  flex: 1;
}
.menu-divider {
  padding: 15px 20px 5px;
  font-size: 12px;
  color: #6b7a90;
}
.main-header {
  background-color: #ffffff;
  border-bottom: 1px solid #e6e6e6;
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0 20px;
}
.header-left {
  display: flex;
  align-items: center;
}
.hamburger {
  font-size: 24px;
  cursor: pointer;
  margin-right: 15px;
  display: none;
}
.page-title {
  font-size: 16px;
  font-weight: bold;
  color: #303133;
}
.user-dropdown {
  display: flex;
  align-items: center;
  cursor: pointer;
  gap: 8px;
}
.username {
  font-size: 14px;
  color: #606266;
}
.main-content {
  background-color: #f0f2f5;
  padding: 20px;
  position: relative;
}
.fade-transform-leave-active,
.fade-transform-enter-active {
  transition: all 0.3s;
}
.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(-20px);
}
.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(20px);
}
@media screen and (max-width: 768px) {
  .pc-aside {
    display: none;
  }
  .hamburger {
    display: block;
  }
  .main-content {
    padding: 10px;
  }
  .page-title {
    font-size: 15px;
  }
  .mobile-logo {
    background-color: #002140;
  }
}
</style>
