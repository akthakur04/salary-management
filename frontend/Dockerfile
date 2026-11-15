# The web app for docker-compose.yml. In production it runs on Vercel instead.
FROM node:22-alpine AS build
WORKDIR /web
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
# The /api/* rewrite target is fixed when the app is built.
ARG API_ORIGIN=http://api:8000
ENV API_ORIGIN=$API_ORIGIN NEXT_TELEMETRY_DISABLED=1
RUN npm run build && npm prune --omit=dev

FROM node:22-alpine
WORKDIR /web
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000
COPY --from=build --chown=node:node /web ./
USER node
EXPOSE 3000
CMD ["npm", "start"]
