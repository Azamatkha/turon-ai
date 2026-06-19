# Frontend "retsept"i: Node + Vite dev server (hot-reload bilan).
# node:20-slim (glibc) — alpine'dagi native binding muammolaridan xoli.
FROM node:20-slim

WORKDIR /app

# Avval faqat package.json (lock'siz) — konteyner linux uchun o'zi toza o'rnatadi
COPY package.json ./
RUN npm install

# Keyin kod
COPY . .

EXPOSE 5173

# Vite dev server (--host => konteyner tashqarisidan ochiq)
CMD ["npm", "run", "dev", "--", "--host"]
