# Stage 1: Build Stage
# Use Node.js 20 Alpine as the base image for a lightweight build environment
FROM node:20-alpine AS build-stage

# Set the working directory inside the container
WORKDIR /app

# Copy package.json and package-lock.json first to leverage Docker layer caching
# This ensures that dependencies are only re-installed when these files change
COPY package*.json ./

# Install project dependencies using npm
RUN npm install

# Copy the rest of the project files to the container
COPY . .

# Build the Vue 3 + Vite application for production
# This will output the built assets to the "dist/" directory
RUN npm run build

# Stage 2: Production Stage
# Use the official Nginx Alpine image for a lightweight and fast web server
FROM nginx:alpine AS production-stage

# Copy the custom Nginx configuration file to the container
# This configuration is crucial to handle Vue Router's History Mode
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Copy the built static assets from the build-stage to Nginx's serving directory
COPY --from=build-stage /app/dist /usr/share/nginx/html

# Expose port 80 to allow external traffic to the web server
EXPOSE 80

# Start Nginx in the foreground so the Docker container doesn't exit
CMD ["nginx", "-g", "daemon off;"]
