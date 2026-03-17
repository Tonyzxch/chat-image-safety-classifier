<template>
  <div class="page">
    <div class="hero">
      <p class="eyebrow">课程项目整理版</p>
      <h1>图片安全分级系统</h1>
      <p class="subtitle">
        这是一个适合公开展示的简化演示页。
        上传图片后，系统会返回风险等级和内容类型两个预测结果。
      </p>
    </div>

    <div class="card">
      <el-upload
        class="upload"
        :action="uploadAction"
        :show-file-list="false"
        :on-success="handleSuccess"
        :on-error="handleError"
        name="file"
      >
        <el-button type="primary" size="medium">上传图片</el-button>
      </el-upload>

      <div class="result" v-if="result">
        <div class="result-row">
          <span class="label">风险等级</span>
          <span class="value">{{ result.danger }}</span>
        </div>
        <div class="result-row">
          <span class="label">内容类型</span>
          <span class="value">{{ result.type }}</span>
        </div>
        <div class="result-row" v-if="result.filename">
          <span class="label">保存文件名</span>
          <span class="value">{{ result.filename }}</span>
        </div>
      </div>

      <el-alert
        v-if="errorMessage"
        :title="errorMessage"
        type="error"
        :closable="false"
        show-icon
      />
    </div>
  </div>
</template>

<script>
export default {
  name: "Predict",
  data() {
    return {
      result: null,
      errorMessage: "",
    };
  },
  computed: {
    uploadAction() {
      return `${this.$apiBaseUrl}predict`;
    },
  },
  methods: {
    handleSuccess(response) {
      this.result = response;
      this.errorMessage = "";
    },
    handleError(error) {
      this.result = null;
      this.errorMessage = "预测请求失败，请确认后端服务已启动，且模型路径已经正确配置。";
      if (error) {
        console.error(error);
      }
    },
  },
};
</script>

<style scoped>
.page {
  max-width: 880px;
  margin: 0 auto;
  padding: 64px 24px;
}

.hero {
  margin-bottom: 28px;
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 12px;
  color: #5d6d7e;
}

h1 {
  margin: 0;
  font-size: 44px;
  line-height: 1.1;
}

.subtitle {
  max-width: 680px;
  margin: 14px 0 0;
  font-size: 17px;
  line-height: 1.7;
  color: #405261;
}

.card {
  padding: 28px;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.92);
  box-shadow: 0 18px 40px rgba(21, 40, 61, 0.08);
}

.upload {
  margin-bottom: 24px;
}

.result {
  display: grid;
  gap: 14px;
}

.result-row {
  display: flex;
  justify-content: space-between;
  padding: 14px 16px;
  border-radius: 12px;
  background: #f5f8fb;
}

.label {
  color: #587086;
  font-weight: 600;
}

.value {
  color: #17202a;
  font-weight: 700;
}
</style>
