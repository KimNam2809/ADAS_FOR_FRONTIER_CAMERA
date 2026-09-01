# Context MUST be frontend/dist-landing, never the RoadWatch repository.
FROM nginx:stable-alpine
COPY . /usr/share/nginx/html/
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 8080
