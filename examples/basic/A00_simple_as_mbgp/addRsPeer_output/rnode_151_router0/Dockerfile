FROM bashayer123/bird_grpc:latest
RUN mkdir -p /usr/share/doc/bird2/examples/
RUN touch /usr/share/doc/bird2/examples/bird.conf
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
COPY d18858afc6bb66ec3a19d872077acfd2 /seedemu_sniffer
COPY 17ac2d812a99a91e7f747e1defb72a29 /seedemu_worker
RUN mkdir /bird
COPY ./bird /bird
WORKDIR /bird
RUN autoreconf -i
RUN ./configure --sysconfdir=/etc/bird
RUN make
RUN make install
ENV LD_LIBRARY_PATH=/bird/proto/mbgp/mBGP/cmake/build:$LD_LIBRARY_PATH
RUN ulimit -c unlimited
ENV CORE_PATTERN=/tmp/core.%e.%p.%t
WORKDIR /
RUN chmod +x /start.sh
RUN chmod +x /seedemu_sniffer
RUN chmod +x /seedemu_worker
COPY 2b0ae038330eccd43095538618caee7d /etc/bird/bird.conf
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
CMD ["/start.sh"]

