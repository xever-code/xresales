<template>
  <div class="changelog-page">
    <el-card shadow="sm" class="timeline-card">
      <template #header>
        <div class="card-header">
          <span>📜 系统更新日志</span>
          <el-tag type="success" effect="dark" round>当前版本：v1.0.2</el-tag>
        </div>
      </template>

      <el-timeline>
        <el-timeline-item timestamp="2026-04-20" placement="top" type="success" size="large">
          <el-card shadow="hover">
            <h3>v1.0.2 <el-tag size="small" type="success" style="margin-left: 8px">Update</el-tag></h3>
            <ul>
              <li><strong>[更正]</strong> 更正工时输入，不再支持跨天填写工时。</li>
              <li><strong>[新增]</strong> 增加统计分析页面，可以查看自己输入工时的情况。</li>
            </ul>
          </el-card>
        </el-timeline-item>

        <el-timeline-item timestamp="2026-04-10" placement="top" type="warning" size="large">
          <el-card shadow="hover" class="old-version">
            <h3>v1.0.1-beta <el-tag size="small" type="warning" style="margin-left: 8px">Beta</el-tag></h3>
            <ul>
              <li><strong>[适配]</strong> 增加了移动端的适配，优化了手机端的交互体验。</li>
              <li><strong>[调整]</strong> 暂时下线了 AI 智能解析录入功能。</li>
              <li><strong>[修复]</strong> 修复了在特定情况下模糊搜索无法匹配到客户名称的问题。</li>
            </ul>
          </el-card>
        </el-timeline-item>

        <el-timeline-item timestamp="2026-04-01" placement="top" color="#909399">
          <el-card shadow="hover" class="old-version">
            <h3>v1.0.0 <el-tag size="small" type="info" style="margin-left: 8px">Initial Release</el-tag></h3>
            <p>IT 售前工作录入系统正式环境搭建完成，基础数据迁移入库。</p>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </el-card>
  </div>
</template>

<style scoped>
.changelog-page {
  padding-bottom: 20px;
  max-width: 900px;
  margin: 0 auto;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: bold;
  color: #409EFF;
  font-size: 16px;
}
h3 {
  margin-top: 0;
  margin-bottom: 10px;
  display: flex;
  align-items: center;
}
ul {
  padding-left: 20px;
  margin: 0;
  color: #606266;
  line-height: 1.8;
}
li strong {
  color: #303133;
}
.old-version h3 {
  color: #909399;
}
.old-version p, .old-version ul {
  color: #909399;
}
.old-version li strong {
  color: #909399;
}
</style>