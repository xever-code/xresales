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

// ----------------------------------------------------
// 👇 替换为：统一高清导出逻辑 (1600 x 800)
// ----------------------------------------------------
const exportHighResChart = (chartInstance, fileName) => {
  // 1. 创建隐藏的临时容器，强制设定物理尺寸为 1600x800
  const hiddenDiv = document.createElement('div')
  hiddenDiv.style.width = '1600px'
  hiddenDiv.style.height = '800px'
  hiddenDiv.style.position = 'absolute'
  hiddenDiv.style.left = '-9999px'
  hiddenDiv.style.visibility = 'hidden'
  document.body.appendChild(hiddenDiv)

  // 2. 初始化临时大尺寸图表，并拷贝原图表的配置
  const tempChart = echarts.init(hiddenDiv)
  const option = chartInstance.getOption()
  
  // 去除动画以加快渲染，并移除右上角的下载工具栏（以免出现在截图里）
  option.animation = false
  if (option.toolbox) option.toolbox = []
  
  // 稍微放大标题字体以适配 1600 宽的大屏
  if (option.title && option.title.length > 0) {
    option.title[0].textStyle = { ...option.title[0].textStyle, fontSize: 22 }
  }

  tempChart.setOption(option)

  // 3. 延迟 500ms 等待 ECharts 渲染完成后，触发高清下载
  setTimeout(() => {
    const url = tempChart.getDataURL({ type: 'png', pixelRatio: 1, backgroundColor: '#fff' })
    const link = document.createElement('a')
    link.download = `${fileName}_${new Date().toISOString().split('T')[0]}.png`
    link.href = url
    link.click()

    // 4. 清理内存和 DOM 垃圾
    tempChart.dispose()
    document.body.removeChild(hiddenDiv)
  }, 500)
}

// 动态生成带有自定义下载功能的 toolbox
const getCustomToolbox = (chartInstance, fileName) => ({
  show: true,
  feature: {
    myDownload: {
      show: true,
      title: '统一尺寸高清下载 (1600x800)',
      // 使用标准的下载 Icon
      icon: 'path://M4.7,22.9L29.3,22.9C30.6,22.9 31.6,21.8 31.6,20.5L31.6,15.8L26.9,15.8L26.9,18.2L9.4,18.2L9.4,15.8L4.7,15.8L4.7,20.5C4.7,21.8 5.7,22.9 7.1,22.9L4.7,22.9ZM16.9,18.2L26.3,8.8L23.0,5.5L19.3,9.2L19.3,0.0L14.6,0.0L14.6,9.2L10.9,5.5L7.6,8.8L16.9,18.2Z',
      onclick: () => exportHighResChart(chartInstance, fileName)
    }
  }
})
// ----------------------------------------------------

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
    toolbox: getCustomToolbox(regionChart, '大区工时投入对比'),
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
      toolbox: getCustomToolbox(userChart, '员工工时投入排行'),
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
    toolbox: getCustomToolbox(hospChart, 'Top客户工时投入'),
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

// 拼接下载饼图 (升级为原生高清重绘，完美统一 1600x800)
const downloadCombinedPies = () => {
  // 获取原图表实例
  const actChart = echarts.getInstanceByDom(actChartRef.value);
  const oppChart = echarts.getInstanceByDom(oppChartRef.value);
  if (!actChart || !oppChart) return;

  // 1. 创建隐藏的 1600x800 高清画板
  const hiddenDiv = document.createElement('div');
  hiddenDiv.style.width = '1600px';
  hiddenDiv.style.height = '800px';
  hiddenDiv.style.position = 'absolute';
  hiddenDiv.style.left = '-9999px';
  hiddenDiv.style.visibility = 'hidden';
  document.body.appendChild(hiddenDiv);

  // 2. 初始化临时大尺寸图表
  const tempChart = echarts.init(hiddenDiv);

  // 3. 提取原有数据
  const actData = actChart.getOption().series[0].data || [];
  const oppData = oppChart.getOption().series[0].data || [];

  // 4. 神奇的 ECharts 魔法：组合为一个全新的双饼图配置
  tempChart.setOption({
    animation: false,
    backgroundColor: '#ffffff',
    title: [
      { text: '🎯 任务类型占比', left: '25%', top: '10%', textAlign: 'center', textStyle: { fontSize: 26, color: '#333' } },
      { text: '💡 业务机会分布', left: '75%', top: '10%', textAlign: 'center', textStyle: { fontSize: 26, color: '#333' } }
    ],
    series: [
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['25%', '55%'], // 把任务类型画在左半边
        data: actData,
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 18 }
      },
      {
        type: 'pie',
        radius: ['40%', '65%'],
        center: ['75%', '55%'], // 把业务机会画在右半边
        data: oppData,
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 18 }
      }
    ]
  });

  // 5. 等待渲染完成，触发完美尺寸的高清下载
  setTimeout(() => {
    const url = tempChart.getDataURL({ type: 'png', pixelRatio: 1, backgroundColor: '#fff' });
    const link = document.createElement('a');
    link.download = `任务与机会工时分析_${new Date().toISOString().split('T')[0]}.png`;
    link.href = url;
    link.click();

    // 6. 清理内存和 DOM
    tempChart.dispose();
    document.body.removeChild(hiddenDiv);
  }, 500);
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