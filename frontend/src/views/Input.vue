<template>
  <div class="input-page">
    <el-card class="form-card" shadow="sm">
      <template #header>
        <div class="card-header">
          <span>✍️ 新增售前工时记录</span>
        </div>
      </template>

      <el-form 
        ref="formRef"
        :model="form" 
        :rules="rules"
        label-position="top" 
        class="responsive-form"
      >
        <div class="section-title">基本信息</div>
        
        <el-form-item label="医院名称" prop="hospital_code">
          <el-select 
            v-model="form.hospital_code" 
            filterable 
            remote 
            reserve-keyword
            placeholder="输入关键字检索医院"
            :remote-method="searchHospitals"
            :loading="searching"
            size="large"
            class="full-width"
          >
            <el-option 
              v-for="item in hospitalOptions" 
              :key="item.value" 
              :label="item.label" 
              :value="item.value" 
            />
          </el-select>
        </el-form-item>

        <el-form-item label="拜访对象" prop="contact_person">
          <el-input v-model="form.contact_person" placeholder="如：王主任 / 李组长" size="large" clearable />
        </el-form-item>

        <div class="time-group">
          <el-form-item label="开始时间" prop="visit_time_start" class="flex-item">
            <el-date-picker 
              v-model="form.visit_time_start" 
              type="datetime" 
              placeholder="选择开始时间" 
              value-format="YYYY-MM-DD HH:mm:ss"
              size="large"
              :editable="false"
              class="full-width"
            />
          </el-form-item>

          <el-form-item label="结束时间" prop="visit_time_end" class="flex-item">
            <el-date-picker 
              v-model="form.visit_time_end" 
              type="datetime" 
              placeholder="选择结束时间" 
              value-format="YYYY-MM-DD HH:mm:ss"
              size="large"
              :editable="false"
              class="full-width"
            />
          </el-form-item>
        </div>

        <el-form-item label="活动目的" prop="purpose">
          <el-input v-model="form.purpose" type="textarea" :rows="3" placeholder="请简述本次交流的核心目的..." />
        </el-form-item>

        <el-divider border-style="dashed" />

        <div class="section-title">工作标签与跟进</div>

        <el-form-item label="任务类型 (可多选)">
          <div class="touch-checkbox-group">
            <el-checkbox-group v-model="form.activity_types">
              <el-checkbox v-for="t in configs.visit_type" :key="t" :label="t" border>
                {{ t }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </el-form-item>

        <el-form-item label="发现的新业务机会 (可多选)">
          <div class="touch-checkbox-group">
            <el-checkbox-group v-model="form.opportunities">
              <el-checkbox v-for="o in configs.opportunity_type" :key="o" :label="o" border>
                {{ o }}
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </el-form-item>

        <el-form-item label="下一步计划">
          <el-input v-model="form.next_step" type="textarea" :rows="3" placeholder="填写后续的行动项或跟进计划..." />
        </el-form-item>

        <div class="action-bar">
          <el-button type="primary" size="large" class="submit-btn" :loading="submitting" @click="submitLog">
            🚀 提 交 工 作 记 录
          </el-button>
        </div>
      </el-form>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import request from '../api/request'

// --- 状态数据 ---
const formRef = ref(null)
const form = ref({
  hospital_code: '',
  contact_person: '',
  visit_time_start: '',
  visit_time_end: '',
  purpose: '',
  activity_types: [],
  opportunities: [],
  next_step: ''
})

const configs = ref({ visit_type: [], opportunity_type: [] })
const hospitalOptions = ref([])
const searching = ref(false)
const submitting = ref(false)

// --- 表单校验规则 ---
const rules = {
  hospital_code: [{ required: true, message: '请选择医院', trigger: 'change' }],
  contact_person: [{ required: true, message: '请填写拜访对象', trigger: 'blur' }],
  visit_time_start: [{ required: true, message: '请选择开始时间', trigger: 'change' }],
  visit_time_end: [{ required: true, message: '请选择结束时间', trigger: 'change' }],
  purpose: [{ required: true, message: '请填写活动目的', trigger: 'blur' }]
}

// --- 初始化与获取字典配置 ---
onMounted(async () => {
  try {
    const res = await request.get('/configs')
    configs.value = res
  } catch (error) {
    console.error('获取配置字典失败', error)
  }
})

// --- 搜索医院 ---
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

// --- 提交表单 ---
const submitLog = async () => {
  if (!formRef.value) return
  
  await formRef.value.validate(async (valid) => {
    if (valid) {
      if (form.value.visit_time_end < form.value.visit_time_start) {
        ElMessage.error('结束时间不能早于开始时间！')
        return
      }

      submitting.value = true
      try {
        await request.post('/logs', form.value)
        ElMessage.success('🎉 提交成功！数据已入库。')
        // 提交成功后重置表单，保留时间方便连续录入
        formRef.value.resetFields()
        form.value.activity_types = []
        form.value.opportunities = []
        form.value.next_step = ''
        hospitalOptions.value = []
      } catch (error) {
        // request.js 会统一处理错误提示
      } finally {
        submitting.value = false
      }
    } else {
      ElMessage.warning('请检查必填项是否已完整填写')
    }
  })
}
</script>

<style scoped>
.input-page {
  display: flex;
  justify-content: center;
  padding-bottom: 80px; /* 为移动端的吸底按钮留出空间 */
}

.form-card {
  width: 100%;
  max-width: 800px;
  border-radius: 12px;
}

.card-header {
  font-weight: bold;
  color: #409EFF;
  font-size: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: bold;
  color: #909399;
  margin-bottom: 15px;
  border-left: 4px solid #409EFF;
  padding-left: 8px;
}

.full-width {
  width: 100%;
}

.time-group {
  display: flex;
  gap: 20px;
}
.flex-item {
  flex: 1;
}

/* 触屏优化的 Checkbox 样式 */
.touch-checkbox-group .el-checkbox {
  margin-right: 10px;
  margin-bottom: 10px;
  border-radius: 6px;
}
.touch-checkbox-group .el-checkbox.is-checked {
  background-color: #ecf5ff;
}

/* --- 响应式设计 --- */
@media screen and (max-width: 768px) {
  .form-card {
    border: none;
    box-shadow: none;
    border-radius: 0;
  }
  
  .time-group {
    flex-direction: column; /* 手机端时间选择器变为上下排布 */
    gap: 0;
  }

  /* 移动端吸底操作栏 */
  .action-bar {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 12px 16px;
    padding-bottom: calc(12px + env(safe-area-inset-bottom));
    background: rgba(255, 255, 255, 0.95);
    backdrop-filter: blur(10px);
    box-shadow: 0 -2px 10px rgba(0,0,0,0.05);
    z-index: 100;
  }

  .submit-btn {
    width: 100%;
    border-radius: 24px;
    font-weight: bold;
  }
}

/* PC 端的按钮样式 */
@media screen and (min-width: 769px) {
  .action-bar {
    margin-top: 30px;
    text-align: center;
  }
  .submit-btn {
    width: 250px;
    border-radius: 8px;
  }
}
</style>
