# ZotBins_RaspPi
This repository contains all code that manages and interacts with the Raspberry Pi's of the ZotBins project. To view the webapp repository please visit: [ZotBins Web App](https://github.com/caojoshua/ZotBins-Web-App). For more information on ZotBins, please visit: [ZotBins Landing Page](https://zotbins.github.io/)

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
4) `python3 ZBinClassDev.py` (please read user notes below)

### Public Users
If you are a public user, please change the last line of code in `ZBinClassDev.py` from `ZotBins(sendData=True)` to `ZotBins(sendData=False)` then run `ZBinClassDev.py` 

### File Setup
You also need to have the following files under the ZBinData:
1) binData.json
You can contact the [Zotbins team](https://zotbins.github.io) for an example setup file or follow the data format
Format:
```json
{"bin": [{"binID": "<binID>", "tippersurl": "<apicall>"}, "<{error defaults}>"]}
```
- "bin" refers to the first set of rules needed to find the binID and api call
- "binID" refers to the raspberry pi ID. This is assigned through you or your organization
- "tippersurl" is the api call used to upload to the local server

### ZotBins Team Users
If you have all the configuration files on the raspberry pi (not on this repository for security reasons) and wish to send data to the [TIPPERS](http://tippersweb.ics.uci.edu/) database, please run the program as is.

## General Debugging
Everytime `ZBinClassDev.py`is run, a log report is created, detailing bin startup and errors. It can be found in the `/logs` of the `ZotBins_RaspPi` folder

### Error Messages
Optionally, you can add another file to configure error reports.
`"errorData.json"` can be used to generate more detailed reports of your errors.
```json
{"data": [{"binID": "<binID>", "tippersurl": "<api call>", "<flags>,"}],
 "messages": [{"<error message id>": "<message>",}]}
```
- `"data"` refers to data needed to call the api
- `"messages"` refers to the error codes used to debug.

Although you have to predict probable failures when writing more detailed errors, a default check using `"ZBinError.py"` will log whenever a sensor has failed.


## Running Remotely
You can also access the Raspberry Pi remotely thru VNC viewer.

### Native Devices
You can download [VNC viewer](https://www.realvnc.com/en/connect/download/viewer/)
Set up your VNC account (email and password) to set up your VNC network

### Raspberry Pi
Open the terminal (`ctrl+alt+t`).
Install VNC by typing `sudo apt install realvnc-vnc-server realvnc-vnc-viewer`.
On the desktop menu, navigate to `Menu>Preferences>Raspberry Pi Configuration>Interfaces`.
Ensure VNC is enabled.
Find the network address by typing `ifconfig`in the terminal under `ipv4`.
Enter the address into VNC viewer.
