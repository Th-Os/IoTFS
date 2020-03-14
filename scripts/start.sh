# start script.
# modifying is mandatory.
sudo umount dir
cd ..
python3 setup.py sdist bdist_wheel
source ../environments/env/bin/activate
which python3
pip3 install --ignore-installed dist/*.whl
python3 examples/example_app/app.py dir --debug
