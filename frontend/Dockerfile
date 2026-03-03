# Build Stage
# Use Node.js 20 Alpine as the base image for a lightweight build environment
FROM node:20-alpine

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first to leverage Docker layer caching
# This ensures that dependencies are only re-installed when these files change
COPY package*.json ./

# Install project dependencies using npm
RUN npm install

# Copy the rest of the project files to the container
COPY . .

# Accept build-time environment variables for Vite
# Vite inlines VITE_* env vars at build time via import.meta.env
ARG VITE_API_URL
ENV VITE_API_URL=${VITE_API_URL}

# Build the Vue 3 + Vite application for production
# This will output the built assets to the "dist/" directory
RUN npm run build

# Copy built assets to the shared volume at /dist
# rm -rf ensures a clean copy on every rebuild
CMD ["sh", "-c", "rm -rf /dist/* && cp -r /app/dist/* /dist/"]
