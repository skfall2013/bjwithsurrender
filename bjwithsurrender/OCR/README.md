```bash
sudo apt install cmake git libjpeg62-turbo-dev gcc g++ imagemagick libv4l-dev -y

#Within Raspberry Pi under Download folder.
git clone https://github.com/jacksonliam/mjpg-streamer.git
cd mjpg-streamer/mjpg-streamer-experimental
make
sudo make install

#Launch MJPG Streamer
./mjpg_streamer -i "./input_uvc.so" -o "./output_http.so -w ./www"

#On the remote labtop, open a browser and type:
http://<your-raspberry-pi-ip>:8080