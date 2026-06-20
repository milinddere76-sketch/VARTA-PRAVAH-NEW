# Build Stage
FROM node:18-alpine as build
WORKDIR /app

# Expose build argument for React environment variable baking
ARG REACT_APP_API_URL
ENV REACT_APP_API_URL=$REACT_APP_API_URL

# In Lean Mode, the context is already inside the frontend folder
COPY package*.json ./
RUN npm install --legacy-peer-deps
COPY . ./
RUN CI=false npm run build

# Production Stage
FROM nginx:stable-alpine
COPY --from=build /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
