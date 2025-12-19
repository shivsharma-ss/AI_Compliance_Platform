FROM node:22-alpine

WORKDIR /app

# Install dependencies separately to leverage Docker cache
COPY package.json package-lock.json ./
RUN npm ci --no-progress --fund=false --audit=false

# Copy application source
COPY . .

# API base for build-time substitution (set via --build-arg)
ARG VITE_API_BASE=http://localhost:8000
ENV VITE_API_BASE=${VITE_API_BASE}

# Build for production
RUN npm run build

# Serve static assets with a lightweight server
RUN npm install -g serve
EXPOSE 8080

CMD ["sh", "-c", "serve -s dist -l ${PORT:-8080}"]
