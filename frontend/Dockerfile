FROM node:20

WORKDIR /app

# Install dependencies strategically to cache layers
COPY package*.json ./
RUN npm install

# Build the production bundle
COPY . .
RUN npm run build

EXPOSE 3000

# Start NextJS in production mode
CMD ["npm", "start"]
