.PHONY: build install

build:
	cargo build --release

install: build
	cp target/release/ha-client /usr/local/bin/
