FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
# --- FAQAT LOKAL: bank proxysi (Kerio) TLS'ni ushlab qoladi, shuning uchun npm
# sertifikatga ishonmaydi. Serverda quyidagi RUN ni izohga oling. ---
RUN npm config set strict-ssl false
# --- lokal blok tugadi ---

RUN npm ci
COPY . .

ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

FROM node:22-alpine AS runner
WORKDIR /app
# --- FAQAT LOKAL: yuqoridagi kabi, bank proxysi uchun. Serverda izohga oling. ---
RUN npm config set strict-ssl false
# --- lokal blok tugadi ---

RUN npm install -g serve
COPY --from=builder /app/dist ./dist
ENV NODE_ENV=production
EXPOSE 3001
HEALTHCHECK --interval=10s --timeout=5s --retries=5 \
  CMD wget -q -O - http://127.0.0.1:3001/ >/dev/null 2>&1 || exit 1
CMD ["serve", "-s", "dist", "-l", "3001"]