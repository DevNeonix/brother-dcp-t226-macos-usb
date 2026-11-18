FROM debian:bookworm-slim
RUN apt-get update && apt-get install -y --no-install-recommends ghostscript perl file && rm -rf /var/lib/apt/lists/*
COPY opt/brother /opt/brother
RUN ln -s x86_64/brdcpt226filter /opt/brother/Printers/dcpt226/lpd/brdcpt226filter && ln -s x86_64/brprintconf_dcpt226 /opt/brother/Printers/dcpt226/lpd/brprintconf_dcpt226
ENV PPD=/opt/brother/Printers/dcpt226/cupswrapper/brother_dcpt226_printer_en.ppd
ENTRYPOINT ["/usr/bin/perl", "/opt/brother/Printers/dcpt226/cupswrapper/brother_lpdwrapper_dcpt226"]
