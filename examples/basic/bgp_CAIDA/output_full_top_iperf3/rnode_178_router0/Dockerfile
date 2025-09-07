FROM bashayer123/bgp_grpc:latest
ENV DEBIAN_FRONTEND=noninteractive

# Keep Debian's example path happy (matches your old behavior)
RUN mkdir -p /usr/share/doc/bird2/examples/ && \
    touch /usr/share/doc/bird2/examples/bird.conf

# Runtime working dir
WORKDIR /

RUN mkdir -p /usr/share/doc/bird2/examples/
RUN touch /usr/share/doc/bird2/examples/bird.conf
# Runtime scripts and helpers
COPY 082b96ec819c95ae773daebde675ef80 /start.sh
COPY d18858afc6bb66ec3a19d872077acfd2 /seedemu_sniffer
COPY 17ac2d812a99a91e7f747e1defb72a29 /seedemu_worker
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
RUN chmod +x /start.sh /seedemu_sniffer /seedemu_worker /interface_setup

# Configs
COPY 2b0ae038330eccd43095538618caee7d /etc/bird/bird.conf
COPY e01e36443f9f72c6204189260d0bd276 /ifinfo.txt
COPY d3d51fdf7f4bad30dc5db560a01ce629 /interface_setup
CMD ["/start.sh"]

