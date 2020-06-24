#!/bin/sh
systemctl stop baremetal-api
root_dir=`dirname $0`
cd $root_dir
echo "$root_dir"
rm -rf build baremetal_api.egg-info

pip uninstall baremetal-api -y
python setup.py install
systemctl  start  baremetal-api
systemctl  status baremetal-api
