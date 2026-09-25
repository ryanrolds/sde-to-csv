SDE_URL := https://developers.eveonline.com/static-data/eve-online-static-data-latest-jsonl.zip
SDE_ZIP := eve-online-static-data-latest-jsonl.zip
SDE_DIR := sde
CSV_DIR := csv
DEST_DIR := ../eve-factory/data/static

.PHONY: all download convert deploy clean

all: convert

download: $(SDE_DIR)

$(SDE_ZIP):
	curl -LO "$(SDE_URL)"

$(SDE_DIR): $(SDE_ZIP)
	unzip -o $< -d $@

convert: $(SDE_DIR)
	python3 convert.py $(SDE_DIR)/ $(CSV_DIR)/

deploy: convert
	mkdir -p $(DEST_DIR)
	cp $(CSV_DIR)/*.csv $(DEST_DIR)/

clean:
	rm -rf $(SDE_DIR) $(CSV_DIR) $(SDE_ZIP)
