### APPENDIX

A: Create a new image of Index File creation, do the below - 

```sh
1. Go to the folder with Dockerfile in it and with files that need to be wrapped as an image, here "kgqa_docker_ss"
2.  docker-sh> docker build --rm --platform linux/amd64 -t kgqa_similarity_search . - Build the image
3.  docker-sh> docker images - Check if the above image is created
4.  docker-sh> docker save -o kgqa_similarity_search.tar kgqa_similarity_search:latest 
5.  gzip -9 kgqa_similarity_search.tar  - Save it as a gzip file, which can be then uploaded on AWS S3 Bucket using the console 
6.  docker-sh> docker builder prune - Clear the unnecessary builds from the docker cache
```

------------------------------------------------------------------