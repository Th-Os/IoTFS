sudo apt-get install ninja-build
wget https://github.com/libfuse/libfuse/releases/download/fuse-$1/fuse-$1.tar.xz
pip3 install meson
tar xf fuse-$1.tar.xz
cd fuse-$1; mkdir build; cd build; meson ..; ninja; sudo ninja install
ls /usr/local/lib
ls /lib
sudo ln -s /usr/local/lib/x86_64-linux-gnu/libfuse3.so.$1 /lib/x86_64-linux-gnu/libfuse3.so.3