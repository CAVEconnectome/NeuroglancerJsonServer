FROM tiangolo/uwsgi-nginx-flask:python3.7

COPY override/nginx.conf /etc/nginx/nginx.conf
RUN mkdir -p /home/nginx/.cloudvolume/secrets && chown -R nginx /home/nginx && usermod -d /home/nginx -s /bin/bash nginx
COPY requirements.txt /app/.
RUN  pip install -r requirements.txt
COPY . /app
