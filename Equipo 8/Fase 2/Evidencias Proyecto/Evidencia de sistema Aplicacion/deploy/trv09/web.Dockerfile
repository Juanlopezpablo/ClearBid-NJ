FROM corestream-trv09-web-base:local
COPY web.conf /etc/nginx/conf.d/default.conf
COPY edge.conf /etc/nginx/trv09-edge.conf
