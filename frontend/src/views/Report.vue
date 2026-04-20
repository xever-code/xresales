<template>
  <div class="report-dashboard">
    <el-card shadow="sm" class="filter-card" style="margin-bottom: 20px;">
      <div class="filter-container">
        <span class="filter-label">🔍 筛选分析：</span>
        
        <el-select 
          v-if="role === 'admin'"
          v-model="selectedRegion" 
          placeholder="全部大区" 
          clearable 
          @change="fetchData"
          style="width: 140px; margin-right: 15px;"
        >
          <el-option v-for="r in regionOptions" :key="r" :label="r" :value="r" />
        </el-select>

        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
          @change="fetchData"
          :shortcuts="shortcuts"
          style="width: 300px;"
        />
      </div>
    </el-card>

    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :xs="24" :sm="10">
        <el-card shadow="hover" header="🌍 各大区工时投入 (基于团队)">
          <div ref="regionChartRef" style="height: 350px;"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="14">
        <el-card shadow="hover" header="🏥 Top 10 客户工时投入">
          <div ref="hospChartRef" style="height: 350px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :xs="24" :sm="12">
        <el-card shadow="hover" header="🎯 任务类型工时占比">
          <div ref="actChartRef" style="height: 350px;"></div>
        </el-card>
      </el-col>
      <el-col :xs="24" :sm="12">
        <el-card shadow="hover" header="💡 业务机会工时分布">
          <div ref="oppChartRef" style="height: 350px;"></div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import request from '../api/request'

const role = ref(localStorage.getItem('role') || 'user')
const dateRange = ref([])
const selectedRegion = ref('')
const regionOptions = ref([])

const shortcuts = [
  { text: '最近一周', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 7); return [start, end] } },
  { text: '最近一月', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 30); return [start, end] } },
  { text: '今年以来', value: () => { const end = new Date(); const start = new Date(new Date().getFullYear(), 0, 1); return [start, end] } }
]

const regionChartRef = ref(null)
const hospChartRef = ref(null)
const actChartRef = ref(null)
const oppChartRef = ref(null)

let charts = []

// 获取可用的大区列表
const fetchRegions = async () => {
  if (role.value === 'admin') {
    try {
      regionOptions.value = await request.get('/users/regions')
    } catch (err) {
      console.error("获取大区列表失败", err)
    }
  }
}

// 获取图表数据
const fetchData = async () => {
  let params = {}
  if (dateRange.value && dateRange.value.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }
  if (selectedRegion.value) {
    params.region = selectedRegion.value
  }

  try {
    const data = await request.get('/stats/summary', { params })
    await nextTick()
    updateCharts(data)
  } catch (err) {
    console.error("获取统计数据失败", err)
  }
}

const updateCharts = (data) => {
  if (charts.length === 0) {
    charts = [
      echarts.init(regionChartRef.value),
      echarts.init(hospChartRef.value),
      echarts.init(actChartRef.value),
      echarts.init(oppChartRef.value)
    ]
  }

  const [regionChart, hospChart, actChart, oppChart] = charts

  // 1. 区域工时分布 (饼图)
  regionChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 小时 ({d}%)' },
    series: [{
      type: 'pie', radius: '60%', data: data.region_stats,
      itemStyle: { borderRadius: 4, borderColor: '#fff', borderWidth: 2 }
    }]
  })

  // 2. 客户投入排行 (条形图)
  hospChart.setOption({
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    grid: { left: '3%', right: '8%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', name: '小时' },
    yAxis: { 
      type: 'category', 
      data: data.hospital_stats.names.reverse(),
      axisLabel: { interval: 0, width: 120, overflow: 'truncate' }
    },
    series: [{ 
      type: 'bar', 
      data: data.hospital_stats.values.reverse(), 
      itemStyle: { color: '#409EFF', borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: 'right' }
    }]
  })

  // 3. 任务类型 (环形图)
  actChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 小时 ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], data: data.activity_stats,
      itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 }
    }]
  })

  // 4. 业务机会 (环形图)
  oppChart.setOption({
    tooltip: { trigger: 'item', formatter: '{b}: {c} 小时 ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], data: data.opportunity_stats,
      itemStyle: { borderRadius: 5, borderColor: '#fff', borderWidth: 2 }
    }]
  })
}

const handleResize = () => charts.forEach(c => c.resize())

onMounted(() => {
  fetchRegions()
  fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.report-dashboard {
  padding-bottom: 20px;
}
.filter-container {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 10px;
}
.filter-label {
  font-weight: bold;
  color: #606266;
}
</style>