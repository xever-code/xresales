<template>
  <div class="user-manage-page">
    <el-card shadow="sm">
      <template #header>
        <div class="card-header">
          <span>👥 员工账号管理</span>
          <el-button type="primary" @click="openDialog('add')">+ 新增员工</el-button>
        </div>
      </template>

      <div class="filter-container">
        <el-input 
          v-model="keyword" 
          placeholder="搜索姓名或账号名" 
          clearable 
          style="width: 250px; margin-right: 15px;"
          @keyup.enter="fetchData"
        ></el-input>
        <el-button type="primary" @click="fetchData">查询</el-button>
      </div>

      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="id" label="ID" width="70" align="center" />
        <el-table-column prop="real_name" label="真实姓名" width="150" />
        <el-table-column prop="username" label="登录账号名" width="150" />
        
        <el-table-column prop="region" label="所属大区" width="150">
          <template #default="{ row }">
            <el-tag v-if="row.region" effect="plain">{{ row.region }}</el-tag>
            <span v-else style="color: #999;">未分配</span>
          </template>
        </el-table-column>
        
        <el-table-column prop="role" label="系统角色" width="120" align="center">
          <template #default="{ row }">
            <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" effect="dark">
              {{ row.role === 'admin' ? '管理员' : '普通用户' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="操作" min-width="250" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" link @click="openDialog('edit', row)">编辑</el-button>
            <el-button size="small" type="warning" link @click="resetPwd(row)">重置密码</el-button>
            <el-button size="small" type="danger" link @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="total"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          @current-change="fetchData"
        />
      </div>
    </el-card>

    <el-dialog 
      v-model="dialogVisible" 
      :title="dialogType === 'add' ? '✨ 新增员工账号' : '✏️ 修改员工信息'" 
      width="450px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="真实姓名" prop="real_name">
          <el-input v-model="form.real_name" placeholder="请输入员工真实姓名" />
        </el-form-item>
        
        <el-form-item label="登录账号" prop="username">
          <el-input v-model="form.username" placeholder="建议使用拼音或工号" />
          <div v-if="dialogType === 'add'" class="tip-text">初始密码默认统一为：123456</div>
        </el-form-item>

        <el-form-item label="所属大区" prop="region">
          <el-input v-model="form.region" placeholder="如：华东一区、Central 等" />
        </el-form-item>

        <el-form-item label="系统角色" prop="role">
          <el-radio-group v-model="form.role">
            <el-radio label="user">普通员工</el-radio>
            <el-radio label="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="submitForm">确定保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import request from '../api/request'

const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 15
const keyword = ref('')

const dialogVisible = ref(false)
const dialogType = ref('add')
const saving = ref(false)
const formRef = ref(null)

const form = ref({
  id: null,
  username: '',
  real_name: '',
  region: '',
  role: 'user'
})

const rules = {
  real_name: [{ required: true, message: '请输入真实姓名', trigger: 'blur' }],
  username: [{ required: true, message: '请输入登录账号名', trigger: 'blur' }],
  role: [{ required: true, message: '请选择系统角色', trigger: 'change' }]
}

const fetchData = async () => {
  loading.value = true
  try {
    const res = await request.get('/users', { 
      params: { page: currentPage.value, size: pageSize, keyword: keyword.value } 
    })
    tableData.value = res.items
    total.value = res.total
  } catch (error) {
    console.error(error)
  } finally {
    loading.value = false
  }
}

const openDialog = (type, row = null) => {
  dialogType.value = type
  if (type === 'edit' && row) {
    form.value = { ...row }
  } else {
    form.value = { id: null, username: '', real_name: '', region: '', role: 'user' }
  }
  dialogVisible.value = true
}

const submitForm = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      saving.value = true
      try {
        if (dialogType.value === 'add') {
          await request.post('/users', form.value)
          ElMessage.success('创建成功！初始密码为：123456')
        } else {
          await request.put(`/users/${form.value.id}`, form.value)
          ElMessage.success('信息更新成功！')
        }
        dialogVisible.value = false
        fetchData()
      } catch (error) {
        // request.js 会抛出错误提示
      } finally {
        saving.value = false
      }
    }
  })
}

const resetPwd = (row) => {
  ElMessageBox.confirm(`确定要将员工【${row.real_name}】的密码重置为 123456 吗？`, '安全警告', {
    confirmButtonText: '确定重置',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await request.put(`/users/${row.id}`, { reset_password: true })
      ElMessage.success('密码重置成功！')
    } catch (err) {
      console.error(err)
    }
  }).catch(() => {})
}

const handleDelete = (row) => {
  ElMessageBox.confirm(`彻底删除员工【${row.real_name}】的账号？此操作不可逆转！`, '危险操作', {
    confirmButtonText: '确定删除',
    cancelButtonText: '取消',
    type: 'error',
  }).then(async () => {
    try {
      await request.delete(`/users/${row.id}`)
      ElMessage.success('删除成功！')
      fetchData()
    } catch (err) {
      console.error(err)
    }
  }).catch(() => {})
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.user-manage-page {
  padding-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  font-size: 16px;
  color: #409EFF;
}
.filter-container {
  margin-bottom: 20px;
  display: flex;
  align-items: center;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
.tip-text {
  font-size: 12px;
  color: #E6A23C;
  line-height: 1.2;
  margin-top: 5px;
}
</style>