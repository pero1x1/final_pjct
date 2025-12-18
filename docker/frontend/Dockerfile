# syntax=docker/dockerfile:1

FROM node:20-alpine AS builder
WORKDIR /frontend
COPY frontend/package.json ./package.json
COPY frontend/build.mjs ./build.mjs
COPY frontend/index.html ./index.html
RUN npm install --no-audit --no-fund
RUN npm run build

FROM nginx:1.27-alpine AS runtime
COPY docker/frontend/default.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /frontend/dist/ /usr/share/nginx/html/
EXPOSE 80
