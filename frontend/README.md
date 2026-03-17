# Frontend

前端模块提供一个基于 Vue 2 和 Element UI 的图片上传演示页面，用于调用后端推理接口并展示分类结果。

## 功能

- 上传单张图片
- 调用后端 `/predict` 接口
- 展示风险等级和内容类型

## 运行方式

```bash
npm install
npm run dev
```

## 配置

默认请求地址为：

```text
http://127.0.0.1:5000/
```

如需修改后端地址，可调整以下文件：

- `src/main.js`
- `config/dev.env.js`
- `config/prod.env.js`

## 目录说明

- `src/components/Predict.vue`：主演示页面
- `src/main.js`：前端入口与接口地址配置
- `src/router/index.js`：路由配置
