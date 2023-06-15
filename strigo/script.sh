#!/bin/bash

apt-get update
apt-get -y install  \
    zip unzip \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | apt-key add -
add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

apt-get update
apt-get -y install docker-ce docker-ce-cli containerd.io

usermod -a -G docker ubuntu

runuser -l ubuntu -c 'curl -s "https://get.sdkman.io" | bash'
runuser -l ubuntu -c 'source "$HOME/.sdkman/bin/sdkman-init.sh" && sdk version && sdk install java 17.0.7-tem && sdk install maven 3.9.2'


wget -qO- https://deb.nodesource.com/setup_14.x | bash -

apt-get update
apt-get -y install  nodejs

npm install -g @vue/cli

