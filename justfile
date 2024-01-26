build_image:
    docker build -t chevdor/lndg -f container/Dockerfile .
    docker images | grep lndg

push_image:
    docker push chevdor/lndg
