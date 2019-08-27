Here are the sensitivity settings for the error detection. The values can be edited between the *'s below.
***
weight:25
pre_ultra:5
post_ultra:25
tippers:5
not_connected:15
***Change the values below for demo testing***
w: True
u: False
o: True

Flags:
ut_ping: counts the # of unsuccessful ping attempts (pre)
ut_pong: counts the # of unsuccessful ping attempts (post)
wt_ping: counts the # of invalid weight attempts
upload_time: counts the # of unsuccessful connection attempts (tippers)
connect_time: counts the # of unsuccessful connection attempts (network)

the settings above affect these pre-set limits below:
UT_MAX (ultrasonic error limit),
WT_MAX (load sensor error limit)
CT_MAX (


ut_on (ultrasonic functional)
wt_on (is load sensor functional)

ut_on, wt_on, connected, and err_state