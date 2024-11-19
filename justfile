build_image:
    #!/usr/bin/env bash
    IMAGE=${IMAGE:-cryptosharks131/lndg}

    # Hacky but the version does not seem to be extracted elsewhere...
    VERSION=$(cat gui/templates/base.html | sed -nE 's/.*LNDg v([0-9]+\.[0-9]+\.[0-9]+).*/\1/p')
    echo "Building image $IMAGE:$VERSION"

    docker build \
        -t $IMAGE:$VERSION \
        -t $IMAGE:latest \
        --build-arg SUPERVISOR=0 \
        -f container/Dockerfile \
        .
    docker images | grep lndg

push_image:
    #!/usr/bin/env bash
    IMAGE=${IMAGE:-cryptosharks131/lndg}
    # Hacky but the version does not seem to be extracted elsewhere...
    VERSION=$(cat gui/templates/base.html | sed -nE 's/.*LNDg v([0-9]+\.[0-9]+\.[0-9]+).*/\1/p')
    docker push $IMAGE:latest
    docker push $IMAGE:$VERSION
