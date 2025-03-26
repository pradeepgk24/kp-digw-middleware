FROM public.ecr.aws/lambda/python:3.9.2822.11.24.13-x86_64

LABEL dock.img.name="base-image-dev.dock.merck.com/nextgen-etl-pipeline/lambda/python/3.9" \
      com.merck.image.description="Ubuntu image for using in Jenkins for building and deployment" \
      com.merck.schema-version="1.0" \
      com.merck.image.snow-id="BABB89999" \
      com.merck.image.maintainer-dl="tiger-team@merck.com"

RUN yum -y update expat

ADD http://certs.merckvip.com/Merckk201CS%20PROD%20R001%20CA%20G2.pem /etc/pki/ca-trust/source/anchors/Merck_ICS_PROD_ROOT_CA_G2.pem
ADD http://certs.merckvip.com/Merckx28ICS%20PROD%20ISSUING%20A%20G2.pem /etc/pki/ca-trust/source/anchors/Merck_ICS_PROD_ISSUING_CA_G2.pem
RUN update-ca-trust

RUN yum -y update expat
