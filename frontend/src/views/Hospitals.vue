<template>
  <div class="hospitals-page">
    <el-card shadow="sm">
      <template #header>
        <div class="card-header">
          <span>🏢 客户管理 (管理员专属)</span>
          <div class="header-actions">
            <el-input 
              v-model="keyword" 
              placeholder="搜索医院名称或编码" 
              clearable 
              @clear="fetchData"
              @keyup.enter="fetchData"
              style="width: 250px; margin-right: 15px;"
            >
              <template #append>
                <el-button @click="fetchData"><el-icon><Search /></el-icon></el-button>
              </template>
            </el-input>

            <el-upload
              class="upload-inline"
              action="/api/hospitals/import"
              :headers="uploadHeaders"
              :show-file-list="false"
              :on-success="handleUploadSuccess"
              :on-error="handleUploadError"
              accept=".xlsx, .xls, .csv"
            >
              <el-button type="primary" :icon="Upload" :loading="uploading">导入 Excel</el-button>
            </el-upload>
            <el-button type="success" :icon="Download" @click="exportExcel" style="margin-left: 10px;">导出全部</el-button>
          </div>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column prop="code" label="医院编码" width="150" />
        <el-table-column prop="name" label="医院名称" min-width="250" show-overflow-tooltip />
        <el-table-column prop="region" label="所属区域" width="150">
          <template #default="{ row }">
            <el-tag size="small" type="info">{{ row.region }}</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-container">
        <el-pagination
          background
          layout="total, prev, pager, next, jumper"
          :total="total"
          v-model:current-page="currentPage"
          :page-size="pageSize"
          @current-change="fetchData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Upload, Download } from '@element-plus/icons-vue'
import request from '../api/request'

const tableData = ref([])
const loading = ref(false)
const uploading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 15
const keyword = ref('')

// 获取 Token 用于 el-upload 上传认证
const uploadHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('access_token')}`
}))

// 获取数据列表
const fetchData = async () => {
  loading.value = true
  try {
    const res = await request.get('/hospitals', {
      params: { page: currentPage.value, size: pageSize, keyword: keyword.value }
    })
    tableData.value = res.items
    total.value = res.total
  } catch (error) {
    console.error('获取客户列表失败', error)
  } finally {
    loading.value = false
  }
}

// 导出 Excel
const exportExcel = async () => {
  try {
    ElMessage.info('正在生成 Excel 文件，请稍候...')
    // 必须设置 responseType 为 blob 以接收二进制流
    const res = await request.get('/hospitals/export', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '客户基础名录.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('导出成功！')
  } catch (error) {
    ElMessage.error('导出失败，请重试')
  }
}

// 导入成功回调
const handleUploadSuccess = (res) => {
  uploading.value = false
  if (res.status === 'success' || res.message) {
    ElMessage.success(res.message || '导入成功！')
    fetchData() // 刷新表格
  } else {
    ElMessage.error('导入出现异常')
  }
}

// 导入失败回调
const handleUploadError = (err) => {
  uploading.value = false
  try {
    const errorMsg = JSON.parse(err.message).detail
    ElMessage.error(`导入失败: ${errorMsg}`)
  } catch (e) {
    ElMessage.error('导入失败，请检查文件格式或网络')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.hospitals-page {
  padding-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  color: #409EFF;
}
.header-actions {
  display: flex;
  align-items: center;
}
.upload-inline {
  display: inline-block;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

/* 移动端适配 */
@media screen and (max-width: 768px) {
  .card-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 15px;
  }
  .header-actions {
    width: 100%;
    flex-wrap: wrap;
    gap: 10px;
  }
  .header-actions .el-input {
    width: 100% !important;
  }
}
</style>

