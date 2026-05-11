<template>
  <div class="report-dashboard">
    <el-card shadow="sm" class="filter-card" style="margin-bottom: 20px;">
      <div class="filter-container">
        <span class="filter-label">🔍 筛选分析：</span>
        
        <el-select 
          v-if="role === 'admin'"
          v-model="selectedRegion" 
          placeholder="筛选大区" 
          @change="fetchData"
          style="width: 220px; margin-right: 15px;"
        >
          <el-option label="全部大区" value="all" />
          <el-option label="全部大区（不含Central）" value="exclude_central" />
          <el-divider style="margin: 4px 0" />
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
      <el-col :span="24">
        <el-card shadow="hover">
          <div ref="regionChartRef" style="height: 380px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <div ref="userChartRef" style="height: 500px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20" style="margin-bottom: 20px;">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: bold; font-size: 16px;">🏥 Top 客户工时投入排行</span>
              <el-button type="success" size="small" @click="exportTop3Hospitals">导出 Top3 客户明细</el-button>
            </div>
          </template>
          <div ref="hospChartRef" style="height: 400px;"></div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="20">
      <el-col :span="24">
        <el-card shadow="hover">
          <template #header>
            <div style="display: flex; justify-content: space-between; align-items: center;">
              <span style="font-weight: bold; font-size: 16px;">🎯 任务类型 & 💡 业务机会工时占比汇总</span>
              <el-button type="primary" size="small" @click="downloadCombinedPies">合并下载图片</el-button>
            </div>
          </template>
          <div style="display: flex; justify-content: space-around; flex-wrap: wrap;">
            <div ref="actChartRef" style="width: 48%; height: 400px; min-width: 320px;"></div>
            <div ref="oppChartRef" style="width: 48%; height: 400px; min-width: 320px;"></div>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import * as echarts from 'echarts'
import request from '../api/request'

const role = ref(localStorage.getItem('role') || 'user')
const dateRange = ref([])
const selectedRegion = ref('exclude_central')
const regionOptions = ref([])

const currentTopHospitals = ref([]) // 👇 新增：用于缓存当前展示的客户名单

const shortcuts = [
  { text: '最近一周', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 7); return [start, end] } },
  { text: '最近一月', value: () => { const end = new Date(); const start = new Date(); start.setTime(start.getTime() - 3600 * 1000 * 24 * 30); return [start, end] } },
  { text: '今年以来', value: () => { const end = new Date(); const start = new Date(new Date().getFullYear(), 0, 1); return [start, end] } }
]

const regionChartRef = ref(null)
const userChartRef = ref(null)
const hospChartRef = ref(null)
const actChartRef = ref(null)
const oppChartRef = ref(null)

let charts = []

const commonToolbox = {
  show: true,
  feature: { saveAsImage: { title: '下载', pixelRatio: 2 } }
}

const fetchRegions = async () => {
  if (role.value === 'admin') {
    try {
      const res = await request.get('/users/regions')
      regionOptions.value = res.filter(r => r.toLowerCase() !== 'central')
    } catch (err) {
      console.error("获取大区失败", err)
    }
  }
}

const fetchData = async () => {
  let params = {}
  if (dateRange.value && dateRange.value.length === 2) {
    params.start_date = dateRange.value[0]
    params.end_date = dateRange.value[1]
  }

  if (selectedRegion.value && selectedRegion.value !== 'all') {
    params.region = selectedRegion.value
  }

  try {
    const data = await request.get('/stats/summary', { params })
    await nextTick()
    updateCharts(data)
  } catch (err) {
    console.error("加载数据失败", err)
  }
}

const updateCharts = (data) => {
  if (charts.length === 0) {
    charts = [
      echarts.init(regionChartRef.value),
      echarts.init(userChartRef.value),
      echarts.init(hospChartRef.value),
      echarts.init(actChartRef.value),
      echarts.init(oppChartRef.value)
    ]
  }

  const [regionChart, userChart, hospChart, actChart, oppChart] = charts

  // 1. 各区工时汇总 (改为左右对比柱状图)
  regionChart.setOption({
    title: { text: '🌍 各区工时投入对比 (售前 vs 售后)', left: 'center' },
    toolbox: commonToolbox,
    tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
    legend: { data: ['售前工时', '售后工时'], top: 30 },
    xAxis: { type: 'category', data: data.region_stats.names, axisLabel: { interval: 0 } },
    yAxis: { type: 'value', name: '小时' },
    series: [
      {
        name: '售前工时', type: 'bar', data: data.region_stats.presales,
        itemStyle: { color: '#409EFF' }, barMaxWidth: 40,
        label: { show: true, position: 'top', formatter: (p) => p.value > 0 ? p.value : '' }
      },
      {
        name: '售后工时', type: 'bar', data: data.region_stats.aftersales,
        itemStyle: { color: '#E6A23C' }, barMaxWidth: 40,
        label: { show: true, position: 'top', formatter: (p) => p.value > 0 ? p.value : '' }
      }
    ]
  })

  // 2. 员工排行 (改为左右对比柱状图)
  if (data.user_stats) {
    userChart.setOption({
      title: { text: '🏆 员工工时投入对比', left: 'center' },
      toolbox: commonToolbox,
      tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
      legend: { data: ['售前工时', '售后工时'], top: 30 },
      xAxis: { type: 'category', data: data.user_stats.names, axisLabel: { interval: 0, rotate: 30 } },
      yAxis: { type: 'value', name: '小时' },
      series: [
        {
          name: '售前工时', type: 'bar', data: data.user_stats.presales,
          itemStyle: { color: '#67C23A' }, barMaxWidth: 40,
          label: { show: true, position: 'top', formatter: (p) => p.value > 0 ? p.value : '' }
        },
        {
          name: '售后工时', type: 'bar', data: data.user_stats.aftersales,
          itemStyle: { color: '#E6A23C' }, barMaxWidth: 40,
          label: { show: true, position: 'top', formatter: (p) => p.value > 0 ? p.value : '' }
        }
      ]
    })
  }

  // ----------------------------------------------------
  // 注意：下面 3.客户投入、4.任务类型、5.业务机会 的代码完全不用动！
  // 保持原有代码不变即可。
  // ----------------------------------------------------

  // 3. 客户投入
  let hospNames = data.hospital_stats?.names || [];
  let hospValues = data.hospital_stats?.values || [];
  
  if (selectedRegion.value !== 'Central' && selectedRegion.value !== 'all') {
    const validIdx = hospNames.reduce((acc, name, i) => {
      if (name !== '研发创新与综合事务') acc.push(i);
      return acc;
    }, []);
    hospNames = validIdx.map(i => hospNames[i]);
    hospValues = validIdx.map(i => hospValues[i]);
  }

  // 👇 新增：将当前显示的客户列表存起来，因为图表数据是倒序的(.reverse)，所以真实的 Top3 在数组末尾
  currentTopHospitals.value = [...hospNames].reverse();

  hospChart.setOption({
    toolbox: commonToolbox,
    tooltip: { trigger: 'axis' },
    grid: { left: '3%', right: '10%', bottom: '3%', containLabel: true },
    xAxis: { type: 'value', name: '小时' },
    yAxis: { type: 'category', inverse: true, data: hospNames },
    series: [{
      type: 'bar', data: hospValues,
      label: { show: true, position: 'right' },
      itemStyle: { color: '#409EFF' }
    }]
  })

  // 4. 任务类型占比
  actChart.setOption({
    title: { text: '🎯 任务类型占比', left: 'center', top: '10' },
    tooltip: { trigger: 'item', formatter: '{b}: {c}h ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], data: data.activity_stats || [],
      label: { show: true, formatter: '{b}\n{d}%' }
    }]
  })

  // 5. 业务机会分布
  oppChart.setOption({
    title: { text: '💡 业务机会分布', left: 'center', top: '10' },
    tooltip: { trigger: 'item', formatter: '{b}: {c}h ({d}%)' },
    series: [{
      type: 'pie', radius: ['40%', '70%'], data: data.opportunity_stats || [],
      label: { show: true, formatter: '{b}\n{d}%' }
    }]
  })
}

// 👇 新增：导出 Top 3 客户记录的专属功能
const exportTop3Hospitals = async () => {
  const top3 = currentTopHospitals.value.slice(0, 3);
  if (top3.length === 0) {
    ElMessage.warning('当前暂无客户数据');
    return;
  }

  ElMessage.info(`正在生成前 3 名客户记录（${top3.join('、')}），请稍候...`);

  // 拼装请求参数
  let params = { hospital_names: top3.join(',') };
  if (selectedRegion.value && selectedRegion.value !== 'all') {
    params.region = selectedRegion.value;
  }
  if (dateRange.value && dateRange.value.length === 2) {
    params.start_date = dateRange.value[0];
    params.end_date = dateRange.value[1];
  }

  try {
    const res = await request.get('/logs/export', { 
      params, 
      responseType: 'blob' // 必须配置，否则下载的 Excel 会损坏
    });
    
    // 创建虚拟 a 标签触发文件下载
    const blob = new Blob([res], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `Top3客户工时明细_${new Date().toISOString().split('T')[0]}.xlsx`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(link.href);
    
    ElMessage.success('Top 3 客户明细导出成功！');
  } catch (err) {
    console.error(err);
    ElMessage.error('导出失败，请检查网络后重试');
  }
}

// 拼接下载饼图
const downloadCombinedPies = () => {
  const canvas1 = actChartRef.value.querySelector('canvas');
  const canvas2 = oppChartRef.value.querySelector('canvas');
  if (!canvas1 || !canvas2) return;

  const combinedCanvas = document.createElement('canvas');
  const ctx = combinedCanvas.getContext('2d');
  combinedCanvas.width = canvas1.width + canvas2.width;
  combinedCanvas.height = Math.max(canvas1.height, canvas2.height);
  
  ctx.fillStyle = '#FFFFFF';
  ctx.fillRect(0, 0, combinedCanvas.width, combinedCanvas.height);
  ctx.drawImage(canvas1, 0, 0);
  ctx.drawImage(canvas2, canvas1.width, 0);

  const link = document.createElement('a');
  link.download = `任务与机会工时分析_${new Date().toISOString().split('T')[0]}.png`;
  link.href = combinedCanvas.toDataURL('image/png');
  link.click();
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