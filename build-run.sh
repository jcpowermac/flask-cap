#!/bin/bash
sudo docker build -t flask-cap-dind .
sudo docker rm -f flask-cap-dind
sudo docker run -d --name flask-cap-dind --privileged -p 9000:9000 -p 8000:8000 flask-cap-dind
sudo docker exec -it flask-cap-dind journalctl -fu gunicorn 
