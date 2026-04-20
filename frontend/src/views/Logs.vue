<template>
  <div class="report-page">
    <el-card shadow="sm">
      <template #header>
        <div class="card-header">
          <span>📊 统计分析与历史记录</span>
          <el-button type="success" :icon="Download" @click="exportExcel">导出 Excel</el-button>
        </div>
      </template>

      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column v-if="role === 'admin'" prop="user_name" label="提交人" width="100" fixed />
        
        <el-table-column v-if="role === 'admin'" prop="region" label="所属区域" width="100" />
        
        <el-table-column prop="hospital_name" label="拜访客户" min-width="180" show-overflow-tooltip />
        <el-table-column prop="contact_person" label="拜访对象" width="120" />
        
        <el-table-column label="拜访时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.visit_time_start) }}
          </template>
        </el-table-column>

        <el-table-column prop="purpose" label="交流目的" min-width="200" show-overflow-tooltip />

        <el-table-column label="任务类型" min-width="150">
          <template #default="{ row }">
            <el-tag 
              v-for="tag in row.activity_types" 
              :key="tag" 
              size="small" 
              style="margin-right: 4px; margin-bottom: 4px;"
            >
              {{ tag }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column label="业务机会" min-width="150">
          <template #default="{ row }">
            <el-tag 
              v-for="opp in row.opportunities" 
              :key="opp" 
              type="success" 
              size="small" 
              style="margin-right: 4px; margin-bottom: 4px;"
            >
              {{ opp }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="next_step" label="下一步计划" min-width="180" show-overflow-tooltip />
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
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download } from '@element-plus/icons-vue' 
import request from '../api/request'

const role = ref(localStorage.getItem('role') || 'user')
const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 15 // 每页显示 15 条

// 获取数据
const fetchData = async () => {
  loading.value = true
  try {
    const res = await request.get('/logs', {
      params: { page: currentPage.value, size: pageSize }
    })
    tableData.value = res.items
    total.value = res.total
  } catch (error) {
    console.error('获取日志失败:', error)
  } finally {
    loading.value = false
  }
}

// 导出 Excel 方法
const exportExcel = async () => {
  try {
    ElMessage.info('正在生成 Excel 文件，请稍候...')
    // 注意：文件下载必须设置 responseType 为 blob
    const res = await request.get('/logs/export', { responseType: 'blob' })
    const url = window.URL.createObjectURL(new Blob([res]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', '工时记录导出.xlsx')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    ElMessage.success('导出成功！')
  } catch (error) {
    ElMessage.error('导出失败，请重试')
  }
}

// 时间格式化工具（只显示到分）
const formatDate = (dateStr) => {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  const y = date.getFullYear()
  const m = String(date.getMonth() + 1).padStart(2, '0')
  const d = String(date.getDate()).padStart(2, '0')
  const hh = String(date.getHours()).padStart(2, '0')
  const mm = String(date.getMinutes()).padStart(2, '0')
  return `${y}-${m}-${d} ${hh}:${mm}`
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.report-page {
  padding-bottom: 20px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  color: #409EFF;
}
.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
