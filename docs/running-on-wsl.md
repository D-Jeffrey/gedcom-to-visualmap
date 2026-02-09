# Running gedcomVisualGUI on Linux (WSL)

## Side by side
Windows and Linux (WSL) running on Windows 11 - WSL version: 2.4.12.0 - Ubuntu 
![img](img/2025-11-wsl-sideby.png)

## CoPilot Guided instuctions for WSL Ubuntu 24.04

### Troubleshooting GTK Warnings
If you see GTK warnings about "Negative content height" or "for_size smaller than min-size" with checkbuttons, install GTK themes and engines:
```
sudo apt update
sudo apt install gtk2-engines gtk2-engines-murrine gtk2-engines-pixbuf
sudo apt install gnome-themes-extra
```

You can also try setting a specific GTK theme:
```
export GTK_THEME=Adwaita
```

Add this to your `~/.bashrc` or `~/.zshrc` to make it permanent:
```
echo 'export GTK_THEME=Adwaita' >> ~/.bashrc
```

1. Install GTK+ 3 Development Packages
Most modern wxPython builds rely on GTK+ 3. You can install the necessary development files with:
```
sudo apt update
sudo apt install libgtk-3-dev pkg-config
```

2. Verify pkg-config and .pc Files
Ensure pkg-config can locate the GTK+ .pc files:
```
pkg-config --modversion gtk+-3.0
```

If this returns a version number, you're good. **If not, check:**
```
ls /usr/lib/x86_64-linux-gnu/pkgconfig/gtk+-*.pc
```


If the .pc file exists but **isn’t found**, add its path to PKG_CONFIG_PATH:
```
export PKG_CONFIG_PATH=/usr/lib/x86_64-linux-gnu/pkgconfig:$PKG_CONFIG_PATH
```

You can add that line to your ~/.bashrc or ~/.zshrc to persist it.
3. Check LD_LIBRARY_PATH
Ensure GTK+ libraries are discoverable:
```
export LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH
```

Again, add this to your shell config file if needed.
4. Install Other Dependencies
wxPython may also need these:
```
sudo apt install libgl1-mesa-dev libglu1-mesa-dev libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
```

5. Try installing via pip (if prebuilt wheels are available, building the wheel for wxpython can take a very long time):
```
pip install wxPython
```


---
---

# OLD do not use
## Linux (WSL - WSL version: 2.4.12.0)
  
```
sudo apt update
sudo apt upgrade
sudo apt install software-properties-common
sudo add-apt-repository 'ppa:deadsnakes/ppa'
sudo apt-get update
sudo apt install python3.10
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.10 1
sudo update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.8 2
sudo update-alternatives --config python3
sudo apt install python3-pip
sudo apt install python3.10-venv
sudo apt install python3-venv python3-pip python3-wheel
sudo apt-get install python3.10-dev
#pip install -U six wheel setuptools
pip install --upgrade pip

```


This seems to work best... (but is not a good idea if you are using 24.4, as it breaks the default python3.12)
```
#sudo apt install xubuntu-desktop
sudo apt install xfce4
sudo apt-get install libgtk-3-dev
sudo apt-get install python3-wxgtk4.0 python3-wxgtk-webview4.0 python3-wxgtk-media4.0 
sudo apt-get install git curl libsdl2-mixer-2.0-0 libsdl2-image-2.0-0 libsdl2-2.0-0
sudo apt-get reinstall ca-certificates
```

Then you can use UXTerm from the Ubuntu menu of your windows Desktop (Slick)
I'm not sure if any of the steps below (Saved for reference) are required or they are covered by the desktop install

This seems to be the way people are going on Linux...

```
sudo apt-get install python3-venv

python3 -m venv gedcom-to-visualmap
source gedcom-to-visualmap/bin/activate
```

Do the install of `wxPython` to make sure it gets configured and setup correctly.   You may need to install or setup other
modules as above like (libgtk-3-dev).  I read that you should *not* every run `pip` with `sudo`

```
pip install wheel
# this attrdict3 is only required for WSL because of issues in the image
pip install -U attrdict3
pip install wxPython
python -m pip install -U -f https://extras.wxpython.org/wxPython4/extras/linux/gtk3/ubuntu-18.04 wxPython
pip install git+https://github.com/D-Jeffrey/gedcom-to-visualmap.git
```

I have not figured out how to use `venv` properly yet, so this a work in progres.

The egg seems to be generally working (thought I don't have a background understanding of eggs).  It appears eggs are obsolute.




# OLD -- OLD -- Saved for reference

I'm not sure if these steps are still required

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


### Return back to [README](../README.md)