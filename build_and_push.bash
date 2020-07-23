docker build -t bms_core:$1 .
docker tag bms_core:$1 harbor.capitalonline.net/bms-test/bms_core:$1
docker push harbor.capitalonline.net/bms-test/bms_core:$1