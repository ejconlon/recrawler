#!/bin/bash

set -eux

rm -rf .build
mkdir -p .build/recrawler

python3 -m pip install -t .build/recrawler -r requirements.txt
cp -r recrawler .build/recrawler/recrawler

pushd .build
    echo -e '#!/bin/bash\nexec python3 -m recrawler.main $@' > recrawler/main.sh
    chmod +x recrawler/main.sh
    zip -rq recrawler.zip recrawler
    unzip -l recrawler.zip
popd
