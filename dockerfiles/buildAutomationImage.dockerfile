FROM base-image.dock.merck.com/ubuntu/20.04/latest:latest
LABEL dock.img.name=nextgen-et1-pipeline-dev.dock.merck.com/build-automation-image-difw-middlewar
      com.merck.image.description="Ubuntu image for using in CICD Automation processes" \
      com.merck.schema-version="1.0" \
      com.merck.image.snow-id="BA0009990" \
      com.merck.image.maintainer-d1="tiger-team@merck.com"

ENV SONARSCANNER_VERSION=6.0.0.4432
ENV PYENV_TAG=v2.3.8
ENV ADDITIONAL_PYTHON_VERSIONS='3.10.9'
COPY dockerfiles/runtime Dependencies/requirements-for-build-jenkins-3.10.9.txt.

ADD http://certs.merckvip.com/Merck%20ICS%20PROD%20ROOT%20CA%20G2.pem /etc/pki/ca-trust/source/anchors/Merck_ICS_PROD_ROOT_CA_G2.pem
ADD http://certs.merckvip.com/Merck%20ICS%20PROD%20ISSUING%20CA%20G2.pem /etc/pki/ca-trust/source/anchors/Merck_ICS_PROD_ESSUNICA.pem


RUN apt-get update && \
    apt-get install -y ca-certificates && \
    update-ca-certificates && \
    apt-get remove -y ca-certificates openssl && \
    apt-get clean && rm -rf /var/cache/apt/lists /var/lib/apt/lists

RUN apt update && apt install -y \
        python3-pip\
        maven \
        openssl \
        openssh-client\
        git \
        nodejs\
        openjdk-8-jdk\
        libssl-dev \
        libbz2-dev\
        libreadline-dev \
        libsqlite3-dev\
        11vm \
        libncurses5-dev \
        libncursesw5-dev\
        tk-dev \
        libffi-dev \
        liblzma-dev\
        python-openssl \
        cargo \
        python3-networkx \
        python3-1dap\
        build-essential python3-dev\
        libldap2-dev libsas 12-dev slapd ldap-utils tox \
        lcov valgrind \
        unzip \
        libaiol \
  && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/pip pip /usr/bin/pip3 1 && \
    update-java-alternatives -s /usr/lib/jvm/java-1.8.0-openjdk-amd64 \
gfyydtdv
RUN cd /tmp && \
    wget https://awscli.amazonaws.com/aws cli-exe-linux-x86_64.zip && \
    unzip awscli-exe-linux-x86_64.zip && \
    mv aws /opt/aws && \
    rm -rf /tmp/*
ENV PATH=/opt/aws/dist:$PATH
USER root
ENV ROOT HOME='/root'
RUN git clone https://github.com/pyenv/pyenv.git $HOME/.pyenv && \
    cd $HOME/.pyenv && \
    git checkout ${PYENV_TAG} && \
    src/configure && make -C src
ENV PYENV_ROOT="${ROOT_HOME}/.pyenv"
ENV PATH="${PYENV_ROOT}/bin:$PATH"
ENV BASH_ENV="/root/init.rc"
RUN echo 'unset BASH_ENV\nif command -v pyenv 1>/dev/null 2>&1; then \n eval "$(pyenv init -) "\nfi'  \
RUN eval "$(pyenv init -)" && \
    for python in ${ADDITIONAL_PYTHON_VERSIONS); do \
        pyenv install "$python"; \
        pyenv shell "Spython"; \
        pip install --upgrade pip=-23.2.1 wheel==0.41.1; \
        pip install --index-url https://artifacts.merck.com/artifactory/api/pypi/pypi-main-dev/simp ## \
    done
RUN wget "https://artifacts.merck.com/artifactory/generic-jfrog-cli-remote-cache/v2/2.9.8/jfrog-cli"  \
    chmod +x jfrog && mv jfrog /usr/bin

# Install nvm with node and npm
ENV NODE_VERSION 17.1.0
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/ve.39.3/install.sh | bash \
    &&~/.nvm/nvm.sh \
    && nvm install $NODE_VERSION\
    && nvm alias default $NODE_VERSION\
    && nvm use default

# Install terraform (for API usage)
ENV TER HOME /tmp/terraform
ENV TER VER 1.0.6

RUN mkdir ${TER_HOME} && \
    cd ${TER HOME} && \
    wget https://releases.hashicorp.com/terraform/${TER_VER}/terraform_${TER_VER}_linux_amd64.zip & \
    unzip terraform_${TER_VER}_linux_amd64.zip && \
    mv terraform /usr/local/bin/ && \
    rm -rf ${TER_HOME} \

# setup oracle paths
ENV ORACLE_HOME=/opt/oracle
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH: $ORACLE_HOME/1ib

# install oracle client library

RUN curl -o instantclient.zip https://artifacts.merck.com/artifactory/generic-rstudio-dev-local/BUI
    && unzip instantclient.zip \
    && mkdir -p $ORACLE_HOME \
    && mv instantclient_21_13 $ORACLE_HOME/lib\
    && rm -f instantclient.zip


# copy libaio.so.1 to the Oracle client library directory
RUN cp $(find / -name libaio.so.1 | head -n 1) $ORACLE_HOME/lib/

ENTRYPOINT ["/bin/bash", "-i"]
