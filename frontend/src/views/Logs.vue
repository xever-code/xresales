<template>
  <div class="report-page">
    <el-card shadow="sm">
      <template #header>
        <div class="card-header">
          <span>📊 统计分析与历史记录</span>
          <div>
            <el-switch
              v-if="role === 'admin'"
              v-model="isMaintenance"
              active-text="系统维护模式 (暂停录入)"
              active-color="#ff4949"
              @change="handleMaintenanceToggle"
              style="margin-right: 20px;"
            />
            <el-button type="success" :icon="Download" @click="exportExcel">导出 Excel</el-button>
          </div>
        </div>
      </template>

      <div class="filter-container" v-if="role === 'admin'">
        <el-select 
          v-model="filterRegion" 
          placeholder="全部区域" 
          clearable 
          style="width: 150px; margin-right: 15px;"
        >
          <el-option v-for="r in regionOptions" :key="r" :label="r" :value="r" />
        </el-select>

        <el-input 
          v-model="filterUserName" 
          placeholder="输入员工姓名" 
          clearable 
          style="width: 180px; margin-right: 15px;"
          @keyup.enter="handleFilter"
        ></el-input>
        
        <el-button type="primary" :icon="Search" @click="handleFilter">查询</el-button>
      </div>

      <el-table :data="tableData" v-loading="loading" border stripe style="width: 100%">
        <el-table-column v-if="role === 'admin'" prop="real_name" label="提交人" width="100" fixed />
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
            <template v-if="row.activity_types && row.activity_types.length > 0">
              <el-tag v-for="tag in row.activity_types" :key="tag" size="small" style="margin-right: 4px; margin-bottom: 4px;">
                {{ tag }}
              </el-tag>
            </template>
            <el-tag v-else type="info" size="small" effect="plain">暂无类型</el-tag>
          </template>
        </el-table-column>

        <el-table-column label="业务机会" min-width="150">
          <template #default="{ row }">
            <template v-if="row.opportunities && row.opportunities.length > 0">
              <el-tag v-for="opp in row.opportunities" :key="opp" type="success" size="small" style="margin-right: 4px; margin-bottom: 4px;">
                {{ opp }}
              </el-tag>
            </template>
            <el-tag v-else type="info" size="small" effect="plain">暂无机会</el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="next_step" label="下一步计划" min-width="180" show-overflow-tooltip />

        <el-table-column label="操作" width="90" fixed="right" align="center">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openEditDialog(row)">编辑</el-button>
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

    <el-dialog v-model="editDialogVisible" title="修改工时记录" width="500px" destroy-on-close>
      <el-form :model="editForm" label-position="top">
        <el-form-item label="拜访客户" required>
          <el-select 
            v-model="editForm.hospital_code" 
            filterable remote reserve-keyword
            placeholder="输入关键字检索医院"
            :remote-method="searchHospitals"
            :loading="searching"
            style="width: 100%"
          >
            <el-option v-for="item in hospitalOptions" :key="item.value" :label="item.label" :value="item.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="开始时间" required>
          <el-date-picker 
            v-model="editForm.visit_time_start" 
            type="datetime" 
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%" 
          />
        </el-form-item>

        <el-form-item label="结束时间" required>
          <el-date-picker 
            v-model="editForm.visit_time_end" 
            type="datetime" 
            value-format="YYYY-MM-DD HH:mm:ss"
            style="width: 100%" 
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editDialogVisible = false">取消</el-button>
          <el-button type="primary" :loading="saving" @click="submitEdit">保存修改</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Download, Search } from '@element-plus/icons-vue'
import request from '../api/request'

const role = ref(localStorage.getItem('role') || 'user')
const tableData = ref([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = 15

const filterRegion = ref('')
const filterUserName = ref('')
const regionOptions = ref([])
const isMaintenance = ref(false)

// ===================================
// 新增：编辑功能相关的状态与逻辑
// ===================================
const editDialogVisible = ref(false)
const saving = ref(false)
const searching = ref(false)
const hospitalOptions = ref([])

const editForm = ref({
  id: null,
  hospital_code: '',
  visit_time_start: '',
  visit_time_end: ''
})

// 时间格式化工具 (用于把接口回传的时间转为选择器需要的完整字符串)
const formatForPicker = (dateStr) => {
  if (!dateStr) return ''
  const d = new Date(dateStr)
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  const hh = String(d.getHours()).padStart(2, '0')
  const mm = String(d.getMinutes()).padStart(2, '0')
  const ss = String(d.getSeconds()).padStart(2, '0')
  return `${y}-${m}-${day} ${hh}:${mm}:${ss}`
}

// 搜索客户
const searchHospitals = async (query) => {
  if (query) {
    searching.value = true
    try {
      const res = await request.get(`/hospitals/search?keyword=${encodeURIComponent(query)}`)
      hospitalOptions.value = res
    } catch (error) {
      console.error(error)
    } finally {
      searching.value = false
    }
  } else {
    hospitalOptions.value = []
  }
}

// 打开编辑弹窗并回显数据
const openEditDialog = (row) => {
  // 预先给下拉框塞入当前客户的名字，防止回显时只显示冷冰冰的代码
  hospitalOptions.value = [{ value: row.hospital_code, label: row.hospital_name }]
  
  editForm.value = {
    id: row.id,
    hospital_code: row.hospital_code,
    visit_time_start: formatForPicker(row.visit_time_start),
    visit_time_end: formatForPicker(row.visit_time_end)
  }
  editDialogVisible.value = true
}

// 提交修改
const submitEdit = async () => {
  if (!editForm.value.hospital_code || !editForm.value.visit_time_start || !editForm.value.visit_time_end) {
    ElMessage.warning('请将客户和时间信息填写完整')
    return
  }

  // 校验时间先后顺序
  let tStart = new Date(editForm.value.visit_time_start.replace(/-/g, '/')).getTime()
  let tEnd = new Date(editForm.value.visit_time_end.replace(/-/g, '/')).getTime()
  if (tEnd < tStart) {
    ElMessage.error('结束时间不能早于开始时间！')
    return
  }

  saving.value = true
  try {
    await request.put(`/logs/${editForm.value.id}`, {
      hospital_code: editForm.value.hospital_code,
      visit_time_start: editForm.value.visit_time_start,
      visit_time_end: editForm.value.visit_time_end
    })
    ElMessage.success('修改成功！')
    editDialogVisible.value = false
    fetchData() // 修改成功后自动刷新表格数据
  } catch (error) {
    console.error(error)
  } finally {
    saving.value = false
  }
}
// ===================================

const fetchMaintenanceStatus = async () => {
  try {
    const res = await request.get('/system/maintenance')
    isMaintenance.value = res.is_maintenance
  } catch (err) {
    console.error('获取系统状态失败')
  }
}

const handleMaintenanceToggle = async (val) => {
  try {
    await request.post('/system/maintenance', { is_maintenance: val })
    ElMessage.success(val ? '已开启系统维护，普通用户将无法录入！' : '已关闭系统维护，恢复正常录入。')
  } catch (err) {
    isMaintenance.value = !val 
    ElMessage.error('设置失败，请重试')
  }
}

const fetchData = async () => {
  loading.value = true
  try {
    const params = { page: currentPage.value, size: pageSize }
    
    if (role.value === 'admin') {
      if (filterRegion.value) params.region = filterRegion.value
      if (filterUserName.value) params.user_name = filterUserName.value
    }

    const res = await request.get('/logs', { params })
    tableData.value = res.items
    total.value = res.total
  } catch (error) {
    console.error('获取日志失败:', error)
  } finally {
    loading.value = false
  }
}

const handleFilter = () => {
  currentPage.value = 1
  fetchData()
}

const fetchRegions = async () => {
  try {
    const res = await request.get('/users/regions')
    regionOptions.value = res || []
  } catch (error) {
    console.error('无法加载区域列表:', error)
  }
}

const exportExcel = async () => {
  try {
    ElMessage.info('正在生成 Excel 文件，请稍候...')
    
    const params = {}
    if (role.value === 'admin') {
      if (filterRegion.value) params.region = filterRegion.value
      if (filterUserName.value) params.user_name = filterUserName.value
    }

    const res = await request.get('/logs/export', { 
      params,
      responseType: 'blob' 
    })
    
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
  if (role.value === 'admin') {
    fetchRegions()
  }
  fetchData()
  fetchMaintenanceStatus()
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
</style>