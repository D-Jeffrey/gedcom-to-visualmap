
# Running gedcomVisualGUI on Linux (WSL)

### WIP, looking for feedback


## Linux (WSL - WSL version: 1.1.3.0)
  
```
sudo apt-get update
sudo apt install python3-pip
```

This is to sets up and and installed X-Windows for WSL using xfce4 using the 
guidance from https://askubuntu.com/questions/1252007/opening-ubuntu-20-04-desktop-on-wsl2/1365455#1365455

```
sudo apt install pkg-config
sudo apt install libgtk-3-dev 

sudo apt install xrdp xfce4
# If asked, select lightdm, although it probably doesn't matter

# Optionally, back up the default config
sudo cp /etc/xrdp/xrdp.ini /etc/xrdp/xrdp.ini.bak
# Windows Pro and higher are often already running RDP on 3389
# Prevent conflicts:
sudo sed -i 's/3389/3390/g' /etc/xrdp/xrdp.ini

# Prevent Wayland from being used in Xrdp
echo "export WAYLAND_DISPLAY=" > ~/.xsessionrc

# Optional, if you only have one desktop environment installed
echo startxfce4 > ~/.xsession 
sudo service xrdp start

```
Now that you have X installed you can access it by logging into it view a Remote Desktop Connection to `localhost:3390`

You will be prompted for you WSL username and password.  (I login the Xorg as the Session type)

```
sudo apt-get install python3-venv

python3 -m venv gedcom-to-visualmap
source gedcom-to-visualmap/bin/activate
```

Do the install of `wxPython` to make sure it gets configured and setup correctly.   You may need to install or setup other
modules as above like (libgtk-3-dev).  I read that you should *not* every run `pip` with `sudo`

```
# this attrdict3 is only required for WSL because of issues in the image
pip install -U attrdict3
pip install wxPython
pip install git+https://github.com/D-Jeffrey/gedcom-to-visualmap.git@v0.2.3
```

I have not figured out how to use `venv` properly yet, so this a work in progres.

The egg seems to be generally working (thought I don't have a background understanding of eggs).  It appears eggs are obsolute.


##Running on Linux (WSL)
Using the steps of download and unzip release 0.2.1
```
pip install -U attrdict3
pip install wxPython
cd gedcom-to-visualmap
pip install -r requirements.txt
python3 gedcomVisualGUI.py 
```

![img](WSL-2023-04-01-bash.png)

![img](WSL-2023-03-31.png)


Trying an alternate approach of:

```
sudo apt install xubuntu-desktop

```

