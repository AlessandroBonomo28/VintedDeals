# VintedDeals
Telegram bot that finds best vinted deals

- Real-time Monitoring: Automatically checks for new items every few minutes.
- Price Filtering: Set a maximum budget for each keyword.
- Multiple Keywords: Track as many items as you want.
- Interactive Menu: Easy-to-use Telegram commands with a custom keyboard.

<img width="765" height="552" alt="Senza nome" src="https://github.com/user-attachments/assets/1872812e-20f9-4886-89d3-9d2c8cb8ba87" />

## Setup
- Install *Python 3.11.0* or later
- Configure bot using [Botfather](https://telegram.me/BotFather#)
- Clone this repository
- `cd VintedDeals`
- Create a virtual environment 
```
 python -v venv env
```
- Create a file named *.env* and insert your telegram bot token
```
TOKEN = "xxxxxxx"
```
- run the environment
 ```
 # If you are using windows Windows
 
 ./env/Scripts/activate
 
 # If you are using Linux
 
 source env/bin/activate
```
- install dependencies
```
 pip install -r requirements.txt
```
- run the bot
```
python vinteddeals.py
```
### Extra
you can enforce the use of the whitelist to allow bot access only to a custom set of users. Set `ENFORCE_WHITELIST` to true and insert your whitelisted chat IDs into `whitelist.json`
