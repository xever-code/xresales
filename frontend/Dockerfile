# frontend/Dockerfile
# 阶段 1: 编译打包
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install --registry=https://registry.npmmirror.com
COPY . .
RUN npm run build

# 阶段 2: Nginx 部署
FROM nginx:alpine
# 复制编译好的静态文件到 Nginx 目录
COPY --from=builder /app/dist /usr/share/nginx/html
# 复制自定义 Nginx 配置文件 (处理跨域和路由)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
