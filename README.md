# ZotBins_RaspPi
This repository contains all code that manages and interacts with the Raspberry Pi's of the ZotBins project. For more information on ZotBins, please visit: [ZotBins Info Video](tinyurl.com/zotbins)

## First Time Github Set-up
If you are using Windows and you do not have git, install [git bash] (https://gitforwindows.org/)

Open Git Bash and set up the global username and global email that is linked with your github account. If you don't want to type in your password all the time, include the third line of code as well.

```sh
git config --global user.name "John Doe"
git config --global user.email johndoe@example.com
git config --global credential.helper wincred
```
To view your configuration information: `git config --global -l`

## First Time Running ZotBins RaspPi

Make sure all electronic components ( load cell + hx711, ultrasonic sensor + voltage converter ) are connected to the Raspberry Pi. 
1) Open Terminal (you can use the short-cut: `ctrl+alt+t`)
2) `git clone https://github.com/okyang/ZotBins_RaspPi.git`
3) `cd ZotBins_RaspPi`
4) `python ZBinMain.py` (please read user notes below)

### Public Users
If you are a public user, please change the last line of code in `ZBinMain.py` from `main()` to `main(SEND_DATA=False)` then run `ZBinMain.py` 

### ZotBins Team Users
If you have all the configuration files on the raspberry pi (not on this repository for security resons) and wish to send data to the [TIPPERS](http://tippersweb.ics.uci.edu/) database, please run the program as is.
