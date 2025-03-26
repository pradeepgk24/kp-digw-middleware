# Use base image
FROM hase-Image.dock.merck.com/ubuntu/2.0/latest:latest

LABEL description="Ubuntu image for CLCD Automation processes" \
      version="1.0" \
      maintainer="dl-tiger-temerck.com"

# Install required dependencies
RUN apt-get update && apt-get install -y \
    openssl \
    openssh-client \
    git \
    nodejs \
    openjdk-8-jdk \
    libssl-dev \
    libreadline-dev \
    libsqlite3-dev \
    libncurses5-dev \
    libncurses-dev \
    tk-dev \
    libffi-dev \
    liblzma-dev \
    python3-pip \
    python3-dev \
    build-essential \
    python3-setuptools \
    python3-venv \
    libldap2-dev \
    libsasl2-dev \
    slapd \
    ldap-utils \
    tox \
    icu-devtools \
    valgrind \
    unzip \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Update Java alternatives
RUN update-alternatives --install /usr/bin/java java /usr/lib/jvm/java-1.8.0-openjdk-amd64/bin/java 1

# Install AWS CLI
RUN cd /tmp && \
    wget https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip && \
    unzip awscli-exe-linux-x86_64.zip && \
    ./aws/install && \
    rm -rf /tmp/awscli-exe-linux-x86_64.zip /tmp/aws

# Install SonarScanner
ENV SONARSCANNER_VERSION=6.0.0.4412
RUN cd /tmp && \
    wget https://binaries.sonarsource.com/Distribution/sonar-scanner-cli/sonar-scanner-cli-${SONARSCANNER_VERSION}-linux.zip && \
    unzip sonar-scanner-cli-${SONARSCANNER_VERSION}-linux.zip && \
    mv sonar-scanner-${SONARSCANNER_VERSION}-linux /opt/sonar-scanner && \
    rm -rf /tmp/sonar-scanner-cli-${SONARSCANNER_VERSION}-linux.zip
ENV PATH="/opt/sonar-scanner/bin:$PATH"

# Install JFrog CLI
RUN wget https://artifacts.merck.com/artifactory/generic-jfrog-cli-remote-cache/v2/2.9.8/jfrog-cli-linux-amd64 && \
    chmod +x jfrog-cli-linux-amd64 && \
    mv jfrog-cli-linux-amd64 /usr/bin/jfrog

# Install Pyenv and Python versions
ENV PYENV_ROOT="$HOME/.pyenv"
ENV PATH="$PYENV_ROOT/bin:$PATH"
RUN git clone https://github.com/pyenv/pyenv.git $PYENV_ROOT && \
    cd $PYENV_ROOT && \
    git checkout ${PYENV_TAG} && \
    src/configure && make -C src
RUN echo 'unset BASH_ENV\nif command -v pyenv 1>/dev/null 2>&1; then \n eval "$(pyenv init --path)"\nfi' >> $HOME/.bashrc
RUN eval "$(pyenv init --path)" && \
    for python in 3.10.9; do \
        pyenv install "$python"; \
        pyenv shell "$python"; \
        pip install --upgrade pip==23.2.1 wheel==0.41.1; \
        pip install --index-url https://artifacts.merck.com/artifactory/api/pypi/pypi-main-dev/simple --no-deps; \
    done

# Install NVM, Node, and NPM
ENV NODE_VERSION=17.1.0
RUN curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.3/install.sh | bash && \
    . ~/.nvm/nvm.sh && \
    nvm install $NODE_VERSION && \
    nvm alias default $NODE_VERSION && \
    nvm use default

# Install Terraform
ENV TER_HOME=/tmp/terraform
ENV TER_VER=1.0.6
RUN mkdir -p $TER_HOME && \
    cd $TER_HOME && \
    wget https://releases.hashicorp.com/terraform/${TER_VER}/terraform_${TER_VER}_linux_amd64.zip && \
    unzip terraform_${TER_VER}_linux_amd64.zip && \
    mv terraform /usr/local/bin/ && \
    rm -rf $TER_HOME

# Setup Oracle Paths
ENV ORACLE_HOME="/opt/oracle"
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:$ORACLE_HOME/lib"
RUN curl -o instantclient.zip https://artifacts.merck.com/artifactory/generic-rstudio-dev-local/BUILDS/Base-R/Sources/instantclient-basiclite-linux-x64-21.13.0.0.0dbru.zip && \
    unzip instantclient.zip && \
    mkdir -p $ORACLE_HOME && \
    mv instantclient_21_13 $ORACLE_HOME/lib && \
    rm -f instantclient.zip
# Copy libaio to Oracle client library directory
RUN cp $(find / -name libaio.so.1 | head -n 1) $ORACLE_HOME/lib/

# Set working directory and entry point
WORKDIR /app
ENTRYPOINT ["/bin/bash", "-l"]
