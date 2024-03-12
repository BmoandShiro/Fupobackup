Dont forget to setup all the settings and do the scan before use.
https://developer.spotify.com for api setup for your spotify account
asana tokens can be found on their developer portal as well.

To confirm spotify auth copy the URL that pops up even though the page says its an error the URL is the valid token you need to paste in ther terminal
If it says spotify instance isnt active then click play on spotify to actiavte instance
f24 is current macro keybind for listen 
run main file


firefoxwebdrivergecko is essential for firefox api usage. 
firefox executable path is self explanatory had this feature fully working till github fucked me so i have to see what format this version requires i forget but not hard to figure out
i should add format examples in the settings text boxes

i am aware audio ducking has a few unintended issues if you try to change volume while active. not sure this feature is even worth debugging but very doable 

show microphones shows you the index number for your mic that you need to set however just dawned on me i didnt make a setting for this in the settings so you add the correct mic index to line 76 of desktop_assistant.py until i add this feature

very aware i didnt implement error handling yet so if you get an error itll likely freeze and need to be killed and restarted.
tried to compile to .exe but failed to get it to work yet.
