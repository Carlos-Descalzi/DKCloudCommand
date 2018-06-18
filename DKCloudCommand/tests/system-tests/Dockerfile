FROM ubuntu:14.04
MAINTAINER Yan Wang <ywang@datakitchen.io>

# Install Python and pip
RUN sudo apt-get update && \
    sudo apt-get install -y python python-dev python-pip libffi-dev libssl-dev
RUN pip install --upgrade setuptools

# Install DKCloudCommand and its dependencies
RUN pip install requests==2.5.3 boto3 DKCloudCommand

RUN mkdir -p /dk/system_tests/kitchens
WORKDIR /dk/system_tests

COPY *.py system.test.config ./

COPY config.json /root/.dk/default/
COPY general-config.json /root/.dk/
COPY .context /root/.dk/

CMD ["python", "/dk/system_tests/TestDemo.py"]
