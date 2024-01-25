build_image:
    docker build -t chevdor/lndg .
    docker images | grep lndg

push_image:
    docker push chevdor/lndg
