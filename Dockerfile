FROM ubuntu:22.04

RUN apt-get -y update && apt-get -y upgrade && apt-get -y clean
RUN apt-get -y install sane sane-utils libusb-0.1-4 img2pdf ghostscript pdftk imagemagick iproute2 netpbm wget graphicsmagick curl vim && apt-get -y clean

RUN cd /tmp && \
	wget https://download.brother.com/welcome/dlf006642/brscan3-0.2.13-1.amd64.deb && \
	dpkg -i /tmp/brscan3-0.2.13-1.amd64.deb && \
	rm /tmp/brscan3-0.2.13-1.amd64.deb

RUN cd /tmp && \
	wget https://download.brother.com/welcome/dlf006652/brscan-skey-0.3.1-2.amd64.deb && \
	dpkg -i /tmp/brscan-skey-0.3.1-2.amd64.deb && \
	rm /tmp/brscan-skey-0.3.1-2.amd64.deb

RUN ln -vs /usr/lib64/libbrscandec*.so* /usr/lib/x86_64-linux-gnu
RUN ln -vs /usr/lib64/sane/libsane-brother*.so* /usr/lib/x86_64-linux-gnu/sane

ADD files/add_scanner.sh /opt/brother/add_scanner.sh

ENV NAME="Scanner"
ENV MODEL="MFC-5490CN"
ENV IPADDRESS="192.168.0.172"
ENV USERNAME="pi-scanner"

EXPOSE 54925
EXPOSE 54921

#directory for scans:
VOLUME /scans

#directory for config files:
VOLUME /opt/brother/scanner/brscan-skey

CMD /opt/brother/add_scanner.sh
