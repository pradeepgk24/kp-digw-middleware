# Use the base image for Python 3.9 in AWS Lambda
FROM base-image-dock.merck.com/nextgen-et-pipeline/lambda/python/3.9/latest:latest

# Add metadata labels
LABEL com.merck.image.name=nextgen-etl-pipeline-dev.dock.merck.com/difw-middleware-api-lambda \
      com.merck.image.description="Image for framework api to be used in aws lambda" \
      com.merck.schema-version="1.0" \
      com.merck.image.snow-id="BA0009990" \
      com.merck.image.maintainer-dl="tiger-team@merck.com"

# Copy requirements for dependencies
COPY dockerfiles/runtimeDependencies/requirements-for-api.txt .

# Add CA certificates
ADD http://certs.merckvip.com/Merck%20ICS%20PROD%20ROOT%20CA%20G2.pem /etc/pki/ca-trust/source/anchors/Merck_ICS_PROD_ROOT_CA_G2.pem
ADD http://certs.merckvip.com/Merck%20ICS%20PROD%20ISSUING%20CA%20G2.pem /etc/pki/ca-trust/source/anchors/Merck_ICS_PROD_ESSUNICA.pem
COPY dockerfiles/ca-bundle.crt /etc/pki/ca-trust/source/anchors/ca-bundle.crt

# Update CA trust
RUN update-ca-trust

# Install system dependencies
RUN yum -y update expat && yum -y install git tar unzip libaio

# Copy target files and extract them
COPY target/. /tmp/
RUN tar -xzvf /tmp/*

# Install Python dependencies
RUN pip3 install -r requirements-for-api.txt --target "${LAMBDA_TASK_ROOT}"

# Install specific sqlalchemy-redshift version without dependencies
RUN pip install sqlalchemy-redshift==0.8.14 --no-deps --target "${LAMBDA_TASK_ROOT}"

# Setup Oracle paths
ENV ORACLE_HOME=/opt/oracle
ENV LD_LIBRARY_PATH=$LD_LIBRARY_PATH:$ORACLE_HOME/lib
#Setup CA bundle
ENV AWS_CA_BUNDLE=/etc/pki/ca-trust/source/anchors/ca-bundle.crt

# Install Oracle client library
RUN curl -o instantclient.zip https://artifacts.merck.com/artifactory/generic-rdstudio-dev-local/BUILDS/Base-R/Sources/instantclient-basiclite-linux-64-21.13.0.0.0dbru.zip && \
    && unzip instantclient.zip \
    && mkdir -p $ORACLE_HOME && \
    && mv instantclient_21_12 $ORACLE_HOME/lib \
    && rm -f instantclient.zip  \

#copy libao.so.1 to the Oracle Client library directory
RUN cp $(find / -name libaio.so.1 | head -n 1) $ORACLE_HOME/lib/

# Set working directory and entry point
CMD ["apt-generators.resources.generator.generators.lambda_handler"]
