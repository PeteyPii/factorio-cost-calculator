#!/bin/bash
set +x
set +e

factorio --dump-data
cp $APPDATA/Factorio/script-output/data-raw-dump.json .
