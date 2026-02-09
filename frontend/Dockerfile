FROM node:20-alpine

WORKDIR /app

# Set API URL environment variable
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

# Copy package files and install dependencies
COPY frontend/package*.json ./
RUN npm install

# Copy all frontend source files
COPY frontend/ .

# Expose port for Vite dev server
EXPOSE 5173

# Run development server (hot reload enabled)
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]