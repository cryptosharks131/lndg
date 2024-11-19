IMAGE := "gitea.k8s.chevdor.cc/chevdor/lndg"

build_image:
    #!/usr/bin/env bash

    docker build -t {{IMAGE}} --build-arg SUPERVISOR=0 -f container/Dockerfile .
    docker images | grep lndg

push_image:
    docker push {{IMAGE}}
